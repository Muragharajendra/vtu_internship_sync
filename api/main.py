from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
import os
import time

from authlib.integrations.starlette_client import OAuth, OAuthError
import razorpay

from .database import engine, Base, get_db
from . import models
from . import schemas
from . import auth
from .sync_runner import start_sync_background


Base.metadata.create_all(bind=engine)

app = FastAPI(title="VTU Sync API")

# OAuth (Google) for social login
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
else:
    oauth = None

# Razorpay client setup (used for payments)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow front-end to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["health"])
def root():
    return {"message": "VTU Sync API is running", "docs": "/docs"}

@app.get("/auth/google/login")
def google_login():
    """Redirect user to Google's OAuth consent screen."""
    if oauth is None:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    return oauth.google.authorize_redirect(redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle callback from Google OAuth and issue a JWT token."""
    if oauth is None:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.parse_id_token(request, token)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {e}")

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google did not return an email")

    # Create user if it doesn't exist
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if not db_user:
        db_user = models.User(
            email=email,
            hashed_password=auth.get_password_hash(os.urandom(16).hex()),
            entries_remaining=0,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )

    redirect_url = f"{FRONTEND_URL}/?token={access_token}"
    return RedirectResponse(redirect_url)

@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Password validation
    if not user.password or len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if len(user.password.encode()) > 72:
        raise HTTPException(status_code=400, detail="Password cannot be longer than 72 bytes.")

    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password, entries_remaining=0)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Note: user.password comes inside UserCreate for simplicity here
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/change-password")
def change_password(req: schemas.PasswordChangeRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not auth.verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = auth.get_password_hash(req.new_password)
    db.commit()
    return {"success": True, "message": "Password changed successfully"}

@app.post("/reset-password")
def reset_password(req: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == req.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.hashed_password = auth.get_password_hash(req.new_password)
    db.commit()
    return {"success": True, "message": "Password reset successful"}

@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/checkout", response_model=schemas.CheckoutResponse)
def checkout(req: schemas.CheckoutRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Pricing
    prices = {"plan_30": 100, "plan_60": 150}
    entries = {"plan_30": 30, "plan_60": 60}

    if req.plan_id not in prices:
        raise HTTPException(status_code=400, detail="Invalid plan")

    base_price = prices[req.plan_id]
    entry_count = entries[req.plan_id]

    final_price = base_price

    # Coupons & Freetrial
    if req.coupon == "FREETRIAL":
        if current_user.has_used_freetrial:
            raise HTTPException(status_code=400, detail="FREETRIAL has already been used on this account.")
        final_price = 0
        entry_count = 2
        current_user.has_used_freetrial = True
    elif req.coupon == "FREETRIAL100":
        # Fully free trial grant: gives 30 diary entries without payment.
        final_price = 0
        entry_count = 30
    elif req.coupon == "FREEFULL":
        # Fully free plan: allows user to claim the full plan without payment.
        # Can be used multiple times if desired.
        final_price = 0
    elif req.coupon == "DISCOUNTOFFER10":
        final_price = base_price * 0.90
    elif req.coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")

    # If the order is free, just apply it.
    if final_price == 0:
        payment = models.Payment(
            user_id=current_user.id,
            amount=0,
            entries_added=entry_count,
            coupon_used=req.coupon,
            status="completed"
        )
        db.add(payment)
        current_user.entries_remaining += entry_count
        db.commit()

        return {
            "success": True,
            "message": "Payment successful",
            "amount_paid": 0,
            "entries_added": entry_count
        }

    # Otherwise, create a Razorpay order and return order info for checkout.
    if razorpay_client is None:
        # Razorpay not configured (common in local/dev). Return a response that will
        # allow the frontend to fall back to the manual UPI payment form.
        return {
            "success": True,
            "message": "Payment provider not configured. Use UPI to pay.",
            "amount_paid": final_price,
            "entries_added": entry_count,
            # Omitting order_id/key_id will cause the frontend to show UPI fallback
            "order_id": None,
            "key_id": None,
            "currency": "INR",
        }

    order_amount = int(final_price * 100)  # Razorpay uses paise
    try:
        razorpay_order = razorpay_client.order.create({
            "amount": order_amount,
            "currency": "INR",
            "receipt": f"vtusync_{current_user.id}_{int(time.time())}",
            "payment_capture": 1
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {e}")

    # Store a pending payment record, to be completed once checkout succeeds.
    payment = models.Payment(
        user_id=current_user.id,
        amount=final_price,
        entries_added=entry_count,
        coupon_used=req.coupon,
        order_id=razorpay_order.get('id'),
        status="pending",
    )
    db.add(payment)
    db.commit()

    return {
        "success": True,
        "message": "Checkout initialized",
        "amount_paid": final_price,
        "entries_added": entry_count,
        "order_id": razorpay_order.get("id"),
        "key_id": RAZORPAY_KEY_ID,
        "currency": "INR"
    }


@app.post("/checkout/verify")
def verify_checkout(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Expected payload: razorpay_payment_id, razorpay_order_id, razorpay_signature
    if razorpay_client is None:
        raise HTTPException(status_code=500, detail="Payment provider not configured")

    payment_id = payload.get("razorpay_payment_id")
    order_id = payload.get("razorpay_order_id")
    signature = payload.get("razorpay_signature")

    if not payment_id or not order_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment verification fields")

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment verification failed: {e}")

    # Find pending payment record
    payment = db.query(models.Payment).filter(
        models.Payment.user_id == current_user.id,
        models.Payment.status == "pending",
        models.Payment.order_id == order_id
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="No pending payment found for this order")

    payment.status = "completed"
    payment.payment_id = payment_id

    current_user.entries_remaining += payment.entries_added
    db.commit()

    return {"success": True, "message": "Payment verified and entries added", "entries_added": payment.entries_added}

@app.post("/start-sync")
def start_sync(req: schemas.SyncRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.entries_remaining <= 0:
        raise HTTPException(status_code=402, detail="No entries remaining. Please subscribe.")
        
    job = models.Job(
        user_id=current_user.id,
        status="pending",
        start_date_filter=req.start_date
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Run in background
    # Pass dict representation to avoid pydantic thread issues
    req_dict = req.dict() if hasattr(req, "dict") else req.model_dump()
    background_tasks.add_task(start_sync_background, job.id, req_dict, db)
    
    return {"job_id": job.id, "status": "started"}

@app.get("/job/{job_id}", response_model=schemas.JobResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return job

@app.get("/job/{job_id}/logs")
def get_job_logs(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {"logs": job.logs}

@app.get("/job/{job_id}/stream")
def get_job_stream(job_id: int):
    from fastapi.responses import FileResponse
    from config import SCREENSHOTS_DIR
    import os
    path = SCREENSHOTS_DIR / f"job_{job_id}_latest.png"
    if path.exists():
        return FileResponse(path, headers={"Cache-Control": "no-store, max-age=0"})
    raise HTTPException(status_code=404, detail="No screenshot yet")

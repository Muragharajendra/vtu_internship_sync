from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from database import engine, Base, get_db
import models
import schemas
import auth
from sync_runner import start_sync_background


Base.metadata.create_all(bind=engine)

app = FastAPI(title="VTU Sync API")

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

@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
        # Freetrial overrides the plan entirely
        final_price = 0
        entry_count = 2
        current_user.has_used_freetrial = True
    elif req.coupon == "DISCOUNTOFFER10":
        final_price = base_price * 0.90
    elif req.coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")
        
    # PAYMENT GATEWAY / UTR Validation
    # We require a 12-digit UTR for any order that has a cost.
    if final_price > 0:
        if not req.utr or not req.utr.isdigit() or len(req.utr) != 12:
            raise HTTPException(status_code=400, detail="A valid 12-digit UPI Transaction Reference (UTR) is required.")

    payment = models.Payment(
        user_id=current_user.id,
        amount=final_price,
        entries_added=entry_count,
        coupon_used=req.coupon
    )
    db.add(payment)
    
    current_user.entries_remaining += entry_count
    db.commit()
    
    return {
        "success": True, 
        "message": "Payment successful", 
        "amount_paid": final_price,
        "entries_added": entry_count
    }

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

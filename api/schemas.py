from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    entries_remaining: int
    is_active: bool

    class Config:
        orm_mode = True
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class SyncRequest(BaseModel):
    start_date: str
    source_email: str
    source_password: str
    dest_email: str
    dest_password: str

class JobResponse(BaseModel):
    id: int
    status: str
    start_date_filter: str
    created_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True

class CheckoutRequest(BaseModel):
    plan_id: str # 'plan_30' or 'plan_60'
    coupon: Optional[str] = None
    utr: Optional[str] = None

class CheckoutResponse(BaseModel):
    success: bool
    message: str
    amount_paid: float
    entries_added: int
    # Razorpay fields (optional; returned when payment provider is configured)
    order_id: Optional[str] = None
    key_id: Optional[str] = None
    currency: Optional[str] = None

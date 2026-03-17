from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
import datetime
from api.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    entries_remaining = Column(Integer, default=0)
    has_used_freetrial = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    jobs = relationship("Job", back_populates="owner")
    payments = relationship("Payment", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending") # pending, running, completed, failed
    start_date_filter = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    logs = Column(String, default="")
    
    owner = relationship("User", back_populates="jobs")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    entries_added = Column(Integer)
    coupon_used = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    payment_id = Column(String, nullable=True)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="payments")

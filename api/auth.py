from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hmac
import hashlib
import os
import binascii

# Disable bcrypt due to passlib/bcrypt compatibility issues in some environments
# Use PBKDF2-SHA256 exclusively for password hashing - it's more reliable
use_bcrypt = False
pwd_context = None

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import database
import models

SECRET_KEY = "SUPER_SECRET_VTU_KEY_CHANGE_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# PBKDF2-SHA256 parameters for fallback hashing
PBKDF2_ITERATIONS = 200_000

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt if available, otherwise use PBKDF2-SHA256"""
    if use_bcrypt and pwd_context:
        try:
            # bcrypt only supports up to 72 bytes
            if len(password.encode()) > 72:
                raise ValueError("Password cannot be longer than 72 bytes. Please use a shorter password.")
            return pwd_context.hash(password[:72])
        except Exception:
            # If bcrypt fails at runtime, fall back to PBKDF2
            pass
    
    # PBKDF2-SHA256 fallback (always available)
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash - supports both bcrypt and PBKDF2-SHA256 formats"""
    # Try PBKDF2 format first (custom format)
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
            iterations = int(parts[1])
            salt = binascii.unhexlify(parts[2])
            stored_dk = binascii.unhexlify(parts[3])
            computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, iterations)
            return hmac.compare_digest(computed, stored_dk)
        except Exception:
            return False
    
    # Try bcrypt format if pwd_context is available
    if use_bcrypt and pwd_context:
        try:
            # bcrypt only supports up to 72 bytes
            if len(plain_password.encode()) > 72:
                return False
            return pwd_context.verify(plain_password[:72], hashed_password)
        except Exception:
            return False
    
    return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

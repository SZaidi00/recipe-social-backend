from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr  
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr                                              # ← Primary field
    password: str
    username: Optional[str] = None                               # ← Optional
    display_name: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class TokenData(BaseModel):
    email: str = None 
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional


class RegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class OCRResponse(BaseModel):
    extracted_text: Dict[str, Any]
    quality: Optional[list] = None
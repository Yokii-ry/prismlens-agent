from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    code: str
    status: str
    message: str
    data: dict[str, EmailStr]

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

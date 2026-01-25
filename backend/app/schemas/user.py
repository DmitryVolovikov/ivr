from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    is_admin: bool
    is_blocked: bool
    must_change_password: bool


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1)
    password: str = Field(min_length=6)
    confirm_password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
    confirm_password: str


class UserUpdate(BaseModel):
    display_name: str = Field(min_length=1)


class UserRoleUpdate(BaseModel):
    is_admin: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class ResetPasswordResponse(BaseModel):
    temporary_password: str

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as PyUUID
from pydantic import BaseModel
from typing import Optional
from jose import jwt
import bcrypt

from app.config import get_db, settings
from app.models.employee import Base, Employee

router = APIRouter(prefix="/auth", tags=["Authentication"])

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --- Models ---

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "security"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True)
    password_hash = Column(Text, nullable=False)
    status = Column(String(50), default="active")
    must_change_password = Column(Boolean, default=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id"))


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "security"}

    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(255), unique=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = {"schema": "security"}

    user_role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security.users.user_id"))
    role_id = Column(UUID(as_uuid=True), ForeignKey("security.roles.role_id"))


# --- Schemas ---

class LoginRequest(BaseModel):
    username: str  # employee_number
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    employee_id: Optional[str]
    employee_number: str
    name: str
    roles: list[str]
    must_change_password: bool = False


class RoleResponse(BaseModel):
    role_id: PyUUID
    role_name: str

    class Config:
        from_attributes = True


# --- Helper: Create user account when employee is created ---

async def create_user_account(db: AsyncSession, employee_id: PyUUID, employee_number: str, email: Optional[str], password: str, role_name: str):
    """Called from employee creation to auto-create login credentials (single role)"""
    user = User(
        username=employee_number,
        email=email,
        password_hash=hash_password(password),
        status="active",
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()

    result = await db.execute(select(Role).where(Role.role_name == role_name))
    role = result.scalars().first()
    if role:
        db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

    return user


async def create_user_account_multi_roles(db: AsyncSession, employee_id: PyUUID, employee_number: str, email: Optional[str], password: str, role_names: list[str]):
    """Called from employee creation to auto-create login credentials (multiple roles)"""
    user = User(
        username=employee_number,
        email=email,
        password_hash=hash_password(password),
        status="active",
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()

    for role_name in role_names:
        result = await db.execute(select(Role).where(Role.role_name == role_name))
        role = result.scalars().first()
        if role:
            db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

    return user


# --- Endpoints ---

class ChangePasswordRequest(BaseModel):
    username: str
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    await db.commit()
    return {"message": "Password changed successfully"}


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role).order_by(Role.role_name))
    return result.scalars().all()


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Find user by username (employee_number)
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid employee ID or password")

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid employee ID or password")

    # Check active
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")

    # Get roles
    result = await db.execute(
        select(Role).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id)
    )
    roles = [r.role_name for r in result.scalars().all()]
    primary_role = roles[0] if roles else "unknown"

    # Get employee name
    name = data.username
    if user.employee_id:
        emp = await db.get(Employee, user.employee_id)
        if emp:
            name = f"{emp.first_name} {emp.last_name or ''}".strip()

    # Generate token
    token = jwt.encode({
        "sub": str(user.user_id),
        "employee_id": str(user.employee_id) if user.employee_id else None,
        "username": user.username,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return AuthResponse(
        token=token,
        user_id=str(user.user_id),
        employee_id=str(user.employee_id) if user.employee_id else None,
        employee_number=user.username,
        name=name,
        roles=roles,
        must_change_password=user.must_change_password or False,
    )

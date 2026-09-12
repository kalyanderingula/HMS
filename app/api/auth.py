import uuid
import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Integer, select, or_, func
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as PyUUID
from pydantic import BaseModel
from typing import Optional, List
from jose import jwt, JWTError
import bcrypt

from app.config import get_db, settings
from app.models.employee import Base, Employee

router = APIRouter(prefix="/auth", tags=["Authentication"])

security_scheme = HTTPBearer(auto_error=False)

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

EMPLOYEE_PORTAL_ROLES = {
    "super_admin", "admin", "hr_manager", "doctor", "telemedicine_doctor",
    "surgeon", "ot_nurse", "anesthesiologist", "nurse", "icu_staff",
    "receptionist", "pharmacist", "lab_technician", "radiologist",
    "accountant", "insurance_officer", "blood_bank_technician", "emergency_staff",
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


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
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id"))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "security"}
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security.users.user_id"))
    login_time = Column(DateTime, default=datetime.utcnow)
    logout_time = Column(DateTime)
    refresh_token_hash = Column(Text)
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime)
    user_agent = Column(Text)
    ip_address = Column(String(255))


class IdentityLink(Base):
    __tablename__ = "identity_links"
    __table_args__ = {"schema": "security"}
    identity_link_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security.users.user_id"), nullable=False)
    identity_type = Column(String(50), nullable=False)
    identity_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


async def link_identity(db: AsyncSession, user_id: PyUUID, identity_type: str, identity_id: PyUUID):
    existing = (await db.execute(select(IdentityLink).where(
        IdentityLink.user_id == user_id, IdentityLink.identity_type == identity_type
    ))).scalars().first()
    if existing:
        existing.identity_id = identity_id
    else:
        db.add(IdentityLink(user_id=user_id, identity_type=identity_type, identity_id=identity_id))


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"schema": "security"}
    reset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security.users.user_id"))
    token_hash = Column(Text, unique=True)
    expires_at = Column(DateTime)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class MultiFactorAuthentication(Base):
    __tablename__ = "multi_factor_authentication"
    __table_args__ = {"schema": "security"}
    mfa_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("security.users.user_id"))
    mfa_type = Column(String(100))
    enabled = Column(Boolean, default=True)
    secret = Column(Text)
    verified_at = Column(DateTime)


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


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "security"}

    permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    permission_code = Column(String(100), unique=True, nullable=False)
    permission_name = Column(String(255), nullable=False)
    module = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "security"}

    role_permission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("security.roles.role_id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("security.permissions.permission_id", ondelete="CASCADE"), nullable=False)


# --- Schemas ---

class LoginRequest(BaseModel):
    username: str  # employee number or email
    password: str
    otp: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user_id: str
    employee_id: Optional[str]
    patient_id: Optional[str] = None
    employee_number: str
    name: str
    roles: list[str]
    must_change_password: bool = False


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _totp(secret: str, offset: int = 0) -> str:
    key = base64.b32decode(secret.upper())
    counter = int(time.time() // 30) + offset
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    index = digest[-1] & 15
    number = (int.from_bytes(digest[index:index + 4], "big") & 0x7fffffff) % 1000000
    return f"{number:06d}"


def _set_auth_cookies(response: Response, access: str, refresh: str):
    options = {"httponly": True, "secure": settings.AUTH_COOKIE_SECURE, "samesite": "lax", "path": "/"}
    response.set_cookie("hms_access", access, max_age=15 * 60, **options)
    response.set_cookie("hms_refresh", refresh, max_age=7 * 86400, **options)


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
        must_change_password=True,
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()
    await link_identity(db, user.user_id, "employee", employee_id)

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
        must_change_password=True,
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()
    await link_identity(db, user.user_id, "employee", employee_id)

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

class ForgotPasswordRequest(BaseModel):
    identifier: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class MFAConfirmRequest(BaseModel):
    code: str


@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme), db: AsyncSession = Depends(get_db)):
    if not auth or not auth.credentials:
        raise HTTPException(status_code=401, detail="Authentication credentials required")
    try:
        payload = jwt.decode(auth.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("username") != data.username:
        raise HTTPException(status_code=403, detail="You can only change your own password")
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(data.new_password.encode()) > 72:
        raise HTTPException(status_code=400, detail="Password must be at most 72 UTF-8 bytes")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    identifier = data.identifier.strip()
    user = (await db.execute(select(User).where(or_(User.username == identifier,
        func.lower(User.email) == identifier.lower())))).scalars().first()
    result = {"message": "If the account exists, password reset instructions have been created"}
    if user:
        raw = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(user_id=user.user_id, token_hash=_token_hash(raw),
                                  expires_at=datetime.utcnow() + timedelta(minutes=30)))
        await db.commit()
        if settings.AUTH_EXPOSE_RESET_TOKEN:
            result["reset_token"] = raw
    return result


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    if len(data.new_password) < 8 or len(data.new_password.encode()) > 72:
        raise HTTPException(400, "Password must be 8 to 72 UTF-8 bytes")
    record = (await db.execute(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == _token_hash(data.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.utcnow(),
    ))).scalars().first()
    if not record:
        raise HTTPException(400, "Reset token is invalid or expired")
    user = await db.get(User, record.user_id)
    user.password_hash = hash_password(data.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used_at = datetime.utcnow()
    sessions = (await db.execute(select(UserSession).where(UserSession.user_id == user.user_id))).scalars().all()
    for session in sessions:
        session.revoked_at = datetime.utcnow()
    await db.commit()
    return {"message": "Password reset successfully"}


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role).where(Role.role_name.in_(EMPLOYEE_PORTAL_ROLES)).order_by(Role.role_name))
    return result.scalars().all()


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, response: Response, request: Request, db: AsyncSession = Depends(get_db)):
    identifier = data.username.strip()
    result = await db.execute(select(User).where(or_(
        User.username == identifier,
        func.lower(User.email) == identifier.lower(),
    )))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid employee ID or password")

    now = datetime.utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail="Account temporarily locked. Try again later")

    # Verify password
    if not verify_password(data.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.AUTH_MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid employee ID or password")

    # Check active
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Account is inactive")

    mfa = (await db.execute(select(MultiFactorAuthentication).where(
        MultiFactorAuthentication.user_id == user.user_id,
        MultiFactorAuthentication.enabled.is_(True),
    ))).scalars().first()
    if mfa and (not mfa.secret or not data.otp or data.otp not in {_totp(mfa.secret, -1), _totp(mfa.secret), _totp(mfa.secret, 1)}):
        raise HTTPException(status_code=401, detail="A valid 6-digit authenticator code is required")
    user.failed_login_attempts = 0
    user.locked_until = None

    # Get roles
    result = await db.execute(
        select(Role).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id)
    )
    roles = [r.role_name for r in result.scalars().all()]
    primary_role = roles[0] if roles else "unknown"

    # Get employee or patient name
    name = data.username
    if user.employee_id:
        emp = await db.get(Employee, user.employee_id)
        if emp:
            name = f"{emp.first_name} {emp.last_name or ''}".strip()
    if user.patient_id:
        from app.models.patient import Patient
        patient = await db.get(Patient, user.patient_id)
        if patient:
            name = f"{patient.first_name} {patient.last_name or ''}".strip()

    # Generate token
    session_id = uuid.uuid4()
    access_payload = {
        "sub": str(user.user_id),
        "employee_id": str(user.employee_id) if user.employee_id else None,
        "patient_id": str(user.patient_id) if user.patient_id else None,
        "username": user.username,
        "roles": roles,
        "sid": str(session_id),
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=15),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh = secrets.token_urlsafe(48)
    db.add(UserSession(session_id=session_id, user_id=user.user_id,
        refresh_token_hash=_token_hash(refresh), expires_at=now + timedelta(days=7),
        user_agent=request.headers.get("user-agent"), ip_address=request.client.host if request.client else None))
    await db.commit()
    _set_auth_cookies(response, token, refresh)

    return AuthResponse(
        token=token,
        user_id=str(user.user_id),
        employee_id=str(user.employee_id) if user.employee_id else None,
        patient_id=str(user.patient_id) if user.patient_id else None,
        employee_number=user.username,
        name=name,
        roles=roles,
        must_change_password=user.must_change_password or False,
    )


# =============================================================================
# JWT Authentication & RBAC Dependencies
# =============================================================================

class CurrentUser(BaseModel):
    user_id: PyUUID
    employee_id: Optional[PyUUID] = None
    patient_id: Optional[PyUUID] = None
    username: str
    roles: List[str]
    name: Optional[str] = None


async def get_current_user(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """Dependency: Decodes and verifies JWT Bearer token, returns authenticated user."""
    credential = auth.credentials if auth and auth.credentials else request.cookies.get("hms_access")
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credential, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str: str = payload.get("sub")
        username: str = payload.get("username")

        if not user_id_str or not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        user_id = PyUUID(user_id_str)
        session_id = payload.get("sid")
        if session_id:
            session = await db.get(UserSession, PyUUID(session_id))
            if not session or session.revoked_at or session.expires_at <= datetime.utcnow():
                raise HTTPException(status_code=401, detail="Session has expired or was revoked")
        # Verify active user in DB
        res = await db.execute(select(User).where(User.user_id == user_id, User.status == "active"))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or disabled")
        if user.username != username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token does not match the user account")

        # Roles are resolved from the database on every request. This makes role
        # changes/revocations effective immediately instead of trusting stale JWT claims.
        role_result = await db.execute(
            select(Role).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user_id)
        )
        roles = [role.role_name for role in role_result.scalars().all()]
        identity_rows = (await db.execute(select(IdentityLink).where(
            IdentityLink.user_id == user_id
        ))).scalars().all()
        identities = {link.identity_type: link.identity_id for link in identity_rows}
        employee_id = identities.get("employee") or user.employee_id
        patient_id = identities.get("patient") or user.patient_id

        # Get name if available
        name = username
        if employee_id:
            emp = await db.get(Employee, employee_id)
            if emp:
                name = f"{emp.first_name} {emp.last_name or ''}".strip()

        return CurrentUser(
            user_id=user_id,
            employee_id=employee_id,
            patient_id=patient_id,
            username=username,
            roles=roles,
            name=name
        )
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: List[str]):
    """RBAC Dependency Factory: Ensures authenticated user holds at least one allowed role."""
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)):
        if not any(role in current_user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Requires one of roles {allowed_roles}"
            )
        return current_user
    return role_checker


@router.get("/me", response_model=CurrentUser)
async def get_my_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Returns the authenticated user's profile and active RBAC roles."""
    return current_user


@router.get("/identity-context")
async def get_identity_context(db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    links = (await db.execute(select(IdentityLink).where(
        IdentityLink.user_id == current_user.user_id
    ))).scalars().all()
    identities = {link.identity_type: str(link.identity_id) for link in links}
    return {
        "user_id": str(current_user.user_id),
        "username": current_user.username,
        "roles": current_user.roles,
        "employee_id": identities.get("employee"),
        "patient_id": identities.get("patient"),
        "doctor_id": identities.get("doctor"),
        "identities": identities,
    }


@router.post("/refresh")
async def refresh_session(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get("hms_refresh")
    if not raw:
        raise HTTPException(401, "Refresh cookie is required")
    session = (await db.execute(select(UserSession).where(
        UserSession.refresh_token_hash == _token_hash(raw),
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > datetime.utcnow(),
    ))).scalars().first()
    if not session:
        raise HTTPException(401, "Refresh session is invalid or expired")
    user = await db.get(User, session.user_id)
    roles = [r.role_name for r in (await db.execute(
        select(Role).join(UserRole, UserRole.role_id == Role.role_id).where(UserRole.user_id == user.user_id)
    )).scalars().all()]
    access = jwt.encode({"sub": str(user.user_id), "employee_id": str(user.employee_id) if user.employee_id else None,
        "patient_id": str(user.patient_id) if user.patient_id else None, "username": user.username,
        "roles": roles, "sid": str(session.session_id), "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=15), "iat": datetime.utcnow()}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    new_refresh = secrets.token_urlsafe(48)
    session.refresh_token_hash = _token_hash(new_refresh)
    await db.commit()
    _set_auth_cookies(response, access, new_refresh)
    return {"token": access}


@router.post("/mfa/setup")
async def setup_mfa(db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    secret = base64.b32encode(secrets.token_bytes(20)).decode()
    record = (await db.execute(select(MultiFactorAuthentication).where(
        MultiFactorAuthentication.user_id == current_user.user_id))).scalars().first()
    if not record:
        record = MultiFactorAuthentication(user_id=current_user.user_id, mfa_type="totp", enabled=False)
        db.add(record)
    record.secret = secret
    record.enabled = False
    await db.commit()
    return {"secret": secret, "otpauth_uri": f"otpauth://totp/HMS:{current_user.username}?secret={secret}&issuer=HMS"}


@router.post("/mfa/confirm")
async def confirm_mfa(data: MFAConfirmRequest, db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    record = (await db.execute(select(MultiFactorAuthentication).where(
        MultiFactorAuthentication.user_id == current_user.user_id))).scalars().first()
    if not record or data.code not in {_totp(record.secret, -1), _totp(record.secret), _totp(record.secret, 1)}:
        raise HTTPException(400, "Invalid authenticator code")
    record.enabled = True
    record.verified_at = datetime.utcnow()
    await db.commit()
    return {"message": "MFA enabled"}


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    credential = request.cookies.get("hms_access")
    if credential:
        try:
            session_id = jwt.decode(credential, JWT_SECRET, algorithms=[JWT_ALGORITHM]).get("sid")
            session = await db.get(UserSession, PyUUID(session_id)) if session_id else None
            if session:
                session.revoked_at = datetime.utcnow()
                session.logout_time = datetime.utcnow()
                await db.commit()
        except (JWTError, ValueError, TypeError):
            pass
    response.delete_cookie("hms_access", path="/")
    response.delete_cookie("hms_refresh", path="/")
    return {"message": f"Successfully logged out user {current_user.username}"}

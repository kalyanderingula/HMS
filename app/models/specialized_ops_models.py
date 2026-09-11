import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base


class PaymentGatewayTransaction(Base):
    __tablename__ = "payment_gateway_transactions"
    __table_args__ = {"schema": "billing"}

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("billing.invoices.invoice_id", ondelete="CASCADE"), nullable=False)
    gateway_provider = Column(String(50), nullable=False)  # Stripe, Razorpay, UPI
    gateway_session_id = Column(String(255), unique=True, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(String(30), default="Pending")  # Pending, Completed, Failed, Cancelled
    payment_reference = Column(String(255), nullable=True)
    signature_verified = Column(Boolean, default=False)
    webhook_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InsurancePreauthorization(Base):
    __tablename__ = "insurance_preauthorizations"
    __table_args__ = {"schema": "billing"}

    preauth_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    insurance_provider = Column(String(255), nullable=False)
    policy_number = Column(String(255), nullable=False)
    approval_code = Column(String(100), unique=True, nullable=False)
    authorized_amount = Column(Numeric(14, 2), nullable=False)
    copay_percentage = Column(Numeric(5, 2), default=0)
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=False)
    status = Column(String(30), default="Approved")  # Approved, Consumed, Expired, Cancelled
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VideoRoom(Base):
    __tablename__ = "video_rooms"
    __table_args__ = {"schema": "telemedicine"}

    room_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    virtual_appointment_id = Column(UUID(as_uuid=True), ForeignKey("telemedicine.virtual_appointments.virtual_appointment_id", ondelete="CASCADE"), nullable=False)
    room_name = Column(String(255), unique=True, nullable=False)
    room_url = Column(String(500), nullable=False)
    host_token = Column(String(255), nullable=True)
    participant_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

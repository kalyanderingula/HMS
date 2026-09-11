import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Boolean, Integer, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.employee import Base

class PharmacyDepartment(Base):
    __tablename__ = "pharmacy_departments"
    __table_args__ = {"schema": "pharmacy"}

    pharmacy_department_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code = Column(String(100), unique=True, nullable=False)
    department_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PharmacyStore(Base):
    __tablename__ = "pharmacy_stores"
    __table_args__ = {"schema": "pharmacy"}

    pharmacy_store_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_code = Column(String(100), unique=True, nullable=False)
    store_name = Column(String(255), nullable=True)
    store_type = Column(String(100), default="Main OPD Pharmacy")
    created_at = Column(DateTime, default=datetime.utcnow)

class Drug(Base):
    __tablename__ = "drugs"
    __table_args__ = {"schema": "pharmacy"}

    drug_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_code = Column(String(100), unique=True, nullable=False)
    generic_name = Column(String(255), nullable=False)
    scientific_name = Column(String(255), nullable=True)
    is_controlled_substance = Column(Boolean, default=False)
    requires_prescription = Column(Boolean, default=True)
    storage_conditions = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"
    __table_args__ = {"schema": "pharmacy"}

    interaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"))
    interacting_drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"))
    interaction_severity = Column(String(100))
    interaction_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class PharmacyInventory(Base):
    __tablename__ = "pharmacy_inventory"
    __table_args__ = {"schema": "pharmacy"}

    inventory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pharmacy_store_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.pharmacy_stores.pharmacy_store_id"), nullable=True)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"), nullable=False)
    available_quantity = Column(Numeric(14, 2), default=0)
    reserved_quantity = Column(Numeric(14, 2), default=0)
    reorder_level = Column(Numeric(14, 2), default=10)
    created_at = Column(DateTime, default=datetime.utcnow)

class PharmacyStockBatch(Base):
    __tablename__ = "pharmacy_stock_batches"
    __table_args__ = {"schema": "pharmacy"}

    batch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.pharmacy_inventory.inventory_id"), nullable=False)
    batch_number = Column(String(255), nullable=False)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False)
    quantity_received = Column(Numeric(14, 2), nullable=False)
    quantity_remaining = Column(Numeric(14, 2), nullable=False)
    purchase_price = Column(Numeric(14, 2), default=0)
    selling_price = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class PrescriptionStatus(Base):
    __tablename__ = "prescription_statuses"
    __table_args__ = {"schema": "pharmacy"}

    prescription_status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = {"schema": "pharmacy"}

    prescription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_number = Column(String(100), unique=True, nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id", ondelete="CASCADE"), nullable=False)
    encounter_id = Column(UUID(as_uuid=True), nullable=True)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)
    prescription_status_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescription_statuses.prescription_status_id"), nullable=True)
    diagnosis = Column(Text, nullable=True)
    prescription_date = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    __table_args__ = {"schema": "pharmacy"}

    prescription_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescriptions.prescription_id", ondelete="CASCADE"), nullable=False)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"), nullable=False)
    medication_record_id = Column(UUID(as_uuid=True), ForeignKey("electronic_medical_records.medication_records.medication_record_id"), nullable=True)
    dosage = Column(String(255), nullable=True)
    frequency = Column(String(255), nullable=True)
    duration = Column(String(255), nullable=True)
    route = Column(String(100), default="Oral")
    quantity_prescribed = Column(Numeric(14, 2), default=1)
    quantity_dispensed = Column(Numeric(14, 2), default=0, nullable=False)
    item_status = Column(String(40), default="Pending", nullable=False)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DispensingRecord(Base):
    __tablename__ = "dispensing_records"
    __table_args__ = {"schema": "pharmacy"}

    dispensing_record_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patient.patients.patient_id"), nullable=True)
    dispensing_reference = Column(String(100), unique=True, nullable=True)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescriptions.prescription_id"), nullable=True)
    dispensed_by = Column(UUID(as_uuid=True), nullable=True)
    dispensing_date = Column(DateTime, default=datetime.utcnow)
    dispensing_status = Column(String(100), default="Completed")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DispensingItem(Base):
    __tablename__ = "dispensing_items"
    __table_args__ = {"schema": "pharmacy"}

    dispensing_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispensing_record_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.dispensing_records.dispensing_record_id", ondelete="CASCADE"), nullable=False)
    prescription_item_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescription_items.prescription_item_id"), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.pharmacy_stock_batches.batch_id"), nullable=False)
    quantity_dispensed = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PrescriptionAmendment(Base):
    __tablename__ = "prescription_amendments"
    __table_args__ = {"schema": "pharmacy"}

    amendment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescriptions.prescription_id"), nullable=False)
    prescription_item_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescription_items.prescription_item_id"))
    action = Column(String(40), nullable=False)
    reason = Column(Text, nullable=False)
    before_value = Column(Text)
    amended_by = Column(UUID(as_uuid=True))
    amended_at = Column(DateTime, default=datetime.utcnow)


class PharmacistReview(Base):
    __tablename__ = "pharmacist_reviews"
    __table_args__ = {"schema": "pharmacy"}

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.prescriptions.prescription_id", ondelete="CASCADE"), nullable=False)
    pharmacist_id = Column(UUID(as_uuid=True), nullable=False)
    review_status = Column(String(30), default="Approved")  # Approved, Flagged, Modified, Rejected
    intervention_type = Column(String(50), default="Routine Cleared")
    clinical_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)


class DrugInteractionRule(Base):
    __tablename__ = "drug_interaction_rules"
    __table_args__ = {"schema": "pharmacy"}

    interaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_a_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"), nullable=False)
    drug_b_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy.drugs.drug_id"), nullable=False)
    severity_level = Column(String(20), default="Moderate")  # Mild, Moderate, Severe, Contraindicated
    description = Column(Text, nullable=True)
    action_required = Column(String(100), default="Monitor patient")
    created_at = Column(DateTime, default=datetime.utcnow)


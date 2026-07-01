import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, ForeignKey, select, or_
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from uuid import UUID as PyUUID
from pydantic import BaseModel
from typing import Optional, List

from app.config import get_db
from app.models.employee import Base, Employee
from app.models.department import Department, SubDepartment

UPLOAD_DIR = "uploads/employee_documents"

router = APIRouter(prefix="/employee-documents", tags=["Employee Documents"])


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"
    __table_args__ = {"schema": "human_resources"}

    employee_document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("human_resources.employees.employee_id"))
    document_name = Column(String(255))
    document_type = Column(String(100))
    document_path = Column(Text)
    uploaded_at = Column(TIMESTAMP)


class DocumentResponse(BaseModel):
    employee_document_id: PyUUID
    employee_id: Optional[PyUUID]
    document_name: Optional[str]
    document_type: Optional[str]
    document_path: Optional[str]
    uploaded_at: Optional[datetime]

    class Config:
        from_attributes = True


class DocumentUpdateRequest(BaseModel):
    document_name: Optional[str] = None
    document_type: Optional[str] = None


class EmployeeSearchResult(BaseModel):
    employee_id: PyUUID
    employee_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    department_name: Optional[str]
    sub_department_name: Optional[str]

    class Config:
        from_attributes = True


# Search employee by code, name, or department
@router.get("/search-employee", response_model=list[EmployeeSearchResult])
async def search_employee(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    query = select(Employee).where(
        or_(
            Employee.employee_number.ilike(f"%{q}%"),
            Employee.first_name.ilike(f"%{q}%"),
            Employee.last_name.ilike(f"%{q}%"),
        )
    )
    result = await db.execute(query)
    employees = result.scalars().all()

    results = []
    for emp in employees:
        dept_name = None
        sub_dept_name = None
        if emp.department_id:
            dept = await db.get(Department, emp.department_id)
            dept_name = dept.department_name if dept else None
        if emp.sub_department_id:
            sub_dept = await db.get(SubDepartment, emp.sub_department_id)
            sub_dept_name = sub_dept.sub_department_name if sub_dept else None

        results.append(EmployeeSearchResult(
            employee_id=emp.employee_id,
            employee_number=emp.employee_number,
            first_name=emp.first_name,
            last_name=emp.last_name,
            department_name=dept_name,
            sub_department_name=sub_dept_name,
        ))
    return results


# Get all documents for a specific employee
@router.get("/by-employee/{employee_id}", response_model=list[DocumentResponse])
async def get_employee_documents(employee_id: PyUUID, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = await db.execute(select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id))
    return result.scalars().all()


# Upload multiple documents for an employee
@router.post("/upload/{employee_id}", response_model=list[DocumentResponse], status_code=201)
async def upload_documents(
    employee_id: PyUUID,
    document_names: List[str] = Form(...),
    document_types: List[str] = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    emp = await db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if not (len(files) == len(document_names) == len(document_types)):
        raise HTTPException(status_code=400, detail="Files, names, and types must have same count")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    uploaded = []

    for file, doc_name, doc_type in zip(files, document_names, document_types):
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        saved_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        doc = EmployeeDocument(
            employee_id=employee_id,
            document_name=doc_name,
            document_type=doc_type,
            document_path=file_path,
            uploaded_at=datetime.utcnow(),
        )
        db.add(doc)
        uploaded.append(doc)

    await db.commit()
    for doc in uploaded:
        await db.refresh(doc)
    return uploaded


# Update document details
@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: PyUUID, data: DocumentUpdateRequest, db: AsyncSession = Depends(get_db)):
    doc = await db.get(EmployeeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if data.document_name:
        doc.document_name = data.document_name
    if data.document_type:
        doc.document_type = data.document_type

    await db.commit()
    await db.refresh(doc)
    return doc


# Delete a document
@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: PyUUID, db: AsyncSession = Depends(get_db)):
    doc = await db.get(EmployeeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.document_path and os.path.exists(doc.document_path):
        os.remove(doc.document_path)

    await db.delete(doc)
    await db.commit()

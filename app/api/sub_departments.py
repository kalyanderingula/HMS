from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from app.config import get_db
from app.models.department import Department, SubDepartment

router = APIRouter(prefix="/sub-departments", tags=["Sub-Departments"])


class SubDepartmentCreate(BaseModel):
    department_id: UUID
    sub_department_code: str
    sub_department_name: str
    description: Optional[str] = None


class SubDepartmentUpdate(BaseModel):
    sub_department_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubDepartmentResponse(BaseModel):
    sub_department_id: UUID
    department_id: UUID
    sub_department_code: str
    sub_department_name: str
    description: Optional[str]
    is_active: Optional[bool]

    class Config:
        from_attributes = True


@router.post("/", response_model=SubDepartmentResponse, status_code=201)
async def create_sub_department(data: SubDepartmentCreate, db: AsyncSession = Depends(get_db)):
    dept = await db.get(Department, data.department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Parent department not found")

    sub_dept = SubDepartment(**data.model_dump())
    db.add(sub_dept)
    await db.commit()
    await db.refresh(sub_dept)
    return sub_dept


@router.get("/", response_model=list[SubDepartmentResponse])
async def list_sub_departments(department_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    query = select(SubDepartment)
    if department_id:
        query = query.where(SubDepartment.department_id == department_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{sub_department_id}", response_model=SubDepartmentResponse)
async def get_sub_department(sub_department_id: UUID, db: AsyncSession = Depends(get_db)):
    sub_dept = await db.get(SubDepartment, sub_department_id)
    if not sub_dept:
        raise HTTPException(status_code=404, detail="Sub-department not found")
    return sub_dept


@router.put("/{sub_department_id}", response_model=SubDepartmentResponse)
async def update_sub_department(sub_department_id: UUID, data: SubDepartmentUpdate, db: AsyncSession = Depends(get_db)):
    sub_dept = await db.get(SubDepartment, sub_department_id)
    if not sub_dept:
        raise HTTPException(status_code=404, detail="Sub-department not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sub_dept, field, value)

    await db.commit()
    await db.refresh(sub_dept)
    return sub_dept

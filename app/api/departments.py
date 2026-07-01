from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from app.config import get_db
from app.models.department import Department

router = APIRouter(prefix="/departments", tags=["Departments"])


class DepartmentCreate(BaseModel):
    department_code: str
    department_name: str
    description: Optional[str] = None
    schema_name: Optional[str] = None


class DepartmentUpdate(BaseModel):
    department_name: Optional[str] = None
    description: Optional[str] = None
    schema_name: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    department_id: UUID
    department_code: str
    department_name: str
    description: Optional[str]
    schema_name: Optional[str]
    is_active: Optional[bool]

    class Config:
        from_attributes = True


@router.post("/", response_model=DepartmentResponse, status_code=201)
async def create_department(data: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    dept = Department(**data.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get("/", response_model=list[DepartmentResponse])
async def list_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(department_id: UUID, db: AsyncSession = Depends(get_db)):
    dept = await db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(department_id: UUID, data: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    dept = await db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dept, field, value)

    await db.commit()
    await db.refresh(dept)
    return dept

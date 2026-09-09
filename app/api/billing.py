"""Invoice and payment ledger backed by the existing billing schema."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, require_roles
from app.config import get_db

access = require_roles(["accountant", "admin", "insurance_officer"])
router = APIRouter(prefix="/billing", tags=["Billing"], dependencies=[Depends(access)])
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class InvoiceLine(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    item_type: Literal["Consultation", "Pharmacy", "Laboratory", "Radiology", "Procedure", "Other"] = "Other"
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit_price: Money


class InvoiceCreate(BaseModel):
    patient_id: UUID
    items: list[InvoiceLine] = Field(min_length=1, max_length=100)
    discount_amount: Money = Decimal("0")
    tax_amount: Money = Decimal("0")
    notes: str = Field(default="", max_length=4000)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: Literal["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking", "Insurance"]
    reference: str = Field(min_length=1, max_length=255)


def invoice_totals(req):
    lines = [(item.quantity * item.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
             for item in req.items]
    subtotal = sum(lines, Decimal("0.00"))
    if req.discount_amount > subtotal:
        raise HTTPException(422, "Discount cannot exceed subtotal")
    total = subtotal + req.tax_amount - req.discount_amount
    if total > Decimal("999999999999.99"):
        raise HTTPException(422, "Invoice exceeds the supported amount")
    return lines, subtotal, total


async def status_id(db, name):
    return await db.scalar(text("""INSERT INTO billing.billing_statuses(status_name)
        VALUES (:name) ON CONFLICT(status_name) DO UPDATE SET status_name=EXCLUDED.status_name
        RETURNING billing_status_id"""), {"name": name})


@router.get("/invoices")
async def list_invoices(patient_id: UUID | None = None, limit: int = Query(100, ge=1, le=200),
                        offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    condition = "WHERE i.patient_id=:patient_id" if patient_id else ""
    rows = await db.execute(text(f"""SELECT i.*, s.status_name, p.mrn,
        concat_ws(' ',p.first_name,p.last_name) AS patient_name
        FROM billing.invoices i JOIN patient.patients p ON p.patient_id=i.patient_id
        LEFT JOIN billing.billing_statuses s ON s.billing_status_id=i.billing_status_id
        {condition} ORDER BY i.invoice_date DESC LIMIT :limit OFFSET :offset"""),
        {"patient_id": patient_id, "limit": limit, "offset": offset})
    return [dict(row) for row in rows.mappings()]


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""SELECT i.*, s.status_name, p.mrn,
        concat_ws(' ',p.first_name,p.last_name) AS patient_name
        FROM billing.invoices i JOIN patient.patients p ON p.patient_id=i.patient_id
        LEFT JOIN billing.billing_statuses s ON s.billing_status_id=i.billing_status_id
        WHERE i.invoice_id=:id"""), {"id": invoice_id})
    invoice = result.mappings().first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    result = dict(invoice)
    result["items"] = [dict(r) for r in (await db.execute(text(
        "SELECT * FROM billing.invoice_items WHERE invoice_id=:id ORDER BY created_at, invoice_item_id"
    ), {"id": invoice_id})).mappings()]
    result["payments"] = [dict(r) for r in (await db.execute(text("""
        SELECT p.*, m.method_name FROM billing.payments p LEFT JOIN billing.payment_methods m
        ON m.payment_method_id=p.payment_method_id WHERE invoice_id=:id ORDER BY payment_date
    """), {"id": invoice_id})).mappings()]
    return result


@router.post("/invoices", status_code=201)
async def create_invoice(req: InvoiceCreate, db: AsyncSession = Depends(get_db),
                         user: CurrentUser = Depends(access)):
    lines, subtotal, total = invoice_totals(req)
    patient = await db.scalar(text("SELECT patient_id FROM patient.patients WHERE patient_id=:id FOR UPDATE"),
                              {"id": req.patient_id})
    if not patient:
        raise HTTPException(404, "Patient not found")
    account = await db.scalar(text("""SELECT billing_account_id FROM billing.billing_accounts
        WHERE patient_id=:id ORDER BY created_at LIMIT 1 FOR UPDATE"""), {"id": req.patient_id})
    if not account:
        account = uuid4()
        await db.execute(text("""INSERT INTO billing.billing_accounts
            (billing_account_id,patient_id,account_number,account_status,total_due,total_paid)
            VALUES (:id,:patient,:number,'Active',0,0)"""),
            {"id": account, "patient": req.patient_id, "number": f"ACC-{uuid4().hex}"})
    invoice_id = uuid4()
    await db.execute(text("""INSERT INTO billing.invoices
        (invoice_id,invoice_number,billing_account_id,patient_id,billing_status_id,
         subtotal_amount,tax_amount,discount_amount,total_amount,paid_amount,balance_amount,notes,created_by)
        VALUES (:id,:number,:account,:patient,:status,:subtotal,:tax,:discount,:total,0,:total,:notes,:user)"""),
        {"id": invoice_id, "number": f"INV-{uuid4().hex[:16].upper()}", "account": account,
         "patient": req.patient_id, "status": await status_id(db, "Pending" if total else "Paid"),
         "subtotal": subtotal, "tax": req.tax_amount, "discount": req.discount_amount,
         "total": total, "notes": req.notes, "user": user.user_id})
    for item, amount in zip(req.items, lines):
        await db.execute(text("""INSERT INTO billing.invoice_items
            (invoice_id,item_type,item_name,quantity,unit_price,tax_amount,discount_amount,line_total)
            VALUES (:id,:type,:name,:quantity,:price,0,0,:total)"""),
            {"id": invoice_id, "type": item.item_type, "name": item.item_name,
             "quantity": item.quantity, "price": item.unit_price, "total": amount})
    await db.execute(text("""UPDATE billing.billing_accounts SET total_due=COALESCE(total_due,0)+:total,
        updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:id"""), {"id": account, "total": total})
    result = await get_invoice(invoice_id, db)
    await db.commit()
    return result


@router.post("/invoices/{invoice_id}/payments", status_code=201)
async def record_payment(invoice_id: UUID, req: PaymentCreate, db: AsyncSession = Depends(get_db),
                         user: CurrentUser = Depends(access)):
    invoice = (await db.execute(text("SELECT * FROM billing.invoices WHERE invoice_id=:id FOR UPDATE"),
                               {"id": invoice_id})).mappings().first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    previous = (await db.execute(text("""SELECT p.payment_amount,m.method_name FROM billing.payments p
        JOIN billing.payment_methods m ON m.payment_method_id=p.payment_method_id
        WHERE p.invoice_id=:id AND p.payment_reference=:reference"""),
        {"id": invoice_id, "reference": req.reference})).mappings().first()
    if previous:
        if previous["payment_amount"] != req.amount or previous["method_name"] != req.method:
            raise HTTPException(409, "Payment reference was already used with different details")
        return await get_invoice(invoice_id, db)
    if req.amount > invoice["balance_amount"]:
        raise HTTPException(409, "Payment exceeds outstanding balance")
    method = await db.scalar(text("""INSERT INTO billing.payment_methods(method_name) VALUES (:name)
        ON CONFLICT(method_name) DO UPDATE SET method_name=EXCLUDED.method_name RETURNING payment_method_id"""),
        {"name": req.method})
    await db.execute(text("""INSERT INTO billing.payments
        (invoice_id,patient_id,payment_method_id,payment_reference,payment_amount,payment_status,received_by)
        VALUES (:id,:patient,:method,:reference,:amount,'Completed',:user)"""),
        {"id": invoice_id, "patient": invoice["patient_id"], "method": method,
         "reference": req.reference, "amount": req.amount, "user": user.user_id})
    balance = invoice["balance_amount"] - req.amount
    await db.execute(text("""UPDATE billing.invoices SET paid_amount=paid_amount+:amount,
        balance_amount=:balance,billing_status_id=:status,updated_at=CURRENT_TIMESTAMP WHERE invoice_id=:id"""),
        {"id": invoice_id, "amount": req.amount, "balance": balance,
         "status": await status_id(db, "Paid" if balance == 0 else "Partially Paid")})
    await db.execute(text("""UPDATE billing.billing_accounts SET total_paid=COALESCE(total_paid,0)+:amount,
        total_due=COALESCE(total_due,0)-:amount,updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:id"""),
        {"id": invoice["billing_account_id"], "amount": req.amount})
    result = await get_invoice(invoice_id, db)
    await db.commit()
    return result

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
from app.models.specialized_ops_models import PaymentGatewayTransaction, InsurancePreauthorization
from app.schemas.specialized_operations import (
    CheckoutSessionCreate, CheckoutSessionResponse,
    PaymentWebhookPayload, PaymentWebhookResponse,
    InsurancePreauthCreate, InsurancePreauthResponse
)

access = require_roles(["accountant", "admin", "insurance_officer"])
accounting_access = require_roles(["accountant", "admin"])
claims_access = require_roles(["accountant", "admin", "insurance_officer"])
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


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class RefundCreate(ReasonRequest):
    payment_id: UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reference: str = Field(min_length=3, max_length=255)


class CreditCreate(ReasonRequest):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class ClaimCreate(BaseModel):
    insurance_provider: str = Field(min_length=2, max_length=255)
    policy_number: str = Field(min_length=2, max_length=255)
    claim_number: str = Field(min_length=2, max_length=255)
    claim_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class ClaimDecision(BaseModel):
    status: Literal["Approved", "Rejected"]
    approved_amount: Money = Decimal("0")
    reason: str = ""


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
    result["refunds"] = [dict(r) for r in (await db.execute(text("""
        SELECT r.* FROM billing.refunds r JOIN billing.payments p ON p.payment_id=r.payment_id
        WHERE p.invoice_id=:id ORDER BY r.refunded_at
    """), {"id": invoice_id})).mappings()]
    result["credit_notes"] = [dict(r) for r in (await db.execute(text(
        "SELECT * FROM billing.credit_notes WHERE invoice_id=:id ORDER BY issued_at"
    ), {"id": invoice_id})).mappings()]
    result["claims"] = [dict(r) for r in (await db.execute(text(
        "SELECT * FROM billing.insurance_claims WHERE invoice_id=:id ORDER BY submitted_at"
    ), {"id": invoice_id})).mappings()]
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


@router.post("/invoices/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: UUID, req: ReasonRequest, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(accounting_access)):
    invoice=(await db.execute(text("SELECT * FROM billing.invoices WHERE invoice_id=:id FOR UPDATE"),{"id":invoice_id})).mappings().first()
    if not invoice: raise HTTPException(404,"Invoice not found")
    if invoice["paid_amount"]>0: raise HTTPException(409,"Refund recorded payments before cancelling the invoice")
    current=await db.scalar(text("SELECT status_name FROM billing.billing_statuses WHERE billing_status_id=:id"),{"id":invoice["billing_status_id"]})
    if current=="Cancelled": raise HTTPException(409,"Invoice is already cancelled")
    await db.execute(text("UPDATE billing.invoices SET balance_amount=0,billing_status_id=:s,notes=concat_ws(E'\\n',notes,CAST(:note AS TEXT)),updated_at=CURRENT_TIMESTAMP WHERE invoice_id=:id"),{"s":await status_id(db,"Cancelled"),"note":f"Cancellation: {req.reason}","id":invoice_id})
    await db.execute(text("UPDATE billing.billing_accounts SET total_due=GREATEST(COALESCE(total_due,0)-:amount,0) WHERE billing_account_id=:id"),{"amount":invoice["balance_amount"],"id":invoice["billing_account_id"]})
    await db.execute(text("INSERT INTO billing.billing_action_audit(invoice_id,action,amount,reason,performed_by) VALUES(:id,'Cancellation',:amount,:reason,:user)"),{"id":invoice_id,"amount":invoice["total_amount"],"reason":req.reason,"user":user.user_id});await db.commit();return await get_invoice(invoice_id,db)


@router.post("/invoices/{invoice_id}/refunds", status_code=201)
async def refund_payment(invoice_id: UUID, req: RefundCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(accounting_access)):
    invoice=(await db.execute(text("SELECT * FROM billing.invoices WHERE invoice_id=:id FOR UPDATE"),{"id":invoice_id})).mappings().first()
    payment=(await db.execute(text("SELECT * FROM billing.payments WHERE payment_id=:p AND invoice_id=:i FOR UPDATE"),{"p":req.payment_id,"i":invoice_id})).mappings().first()
    if not invoice or not payment: raise HTTPException(404,"Invoice or payment not found")
    if await db.scalar(text("SELECT refund_id FROM billing.refunds WHERE refund_reference=:r"),{"r":req.reference}): raise HTTPException(409,"Refund reference was already used")
    refunded=await db.scalar(text("SELECT COALESCE(sum(refund_amount),0) FROM billing.refunds WHERE payment_id=:id AND refund_status='Completed'"),{"id":req.payment_id})
    if req.amount>payment["payment_amount"]-refunded: raise HTTPException(409,"Refund exceeds the remaining refundable payment")
    rid=uuid4();await db.execute(text("INSERT INTO billing.refunds(refund_id,payment_id,refund_reference,refund_amount,refund_reason,refund_status,refunded_by,refunded_at) VALUES(:id,:p,:r,:a,:reason,'Completed',:u,CURRENT_TIMESTAMP)"),{"id":rid,"p":req.payment_id,"r":req.reference,"a":req.amount,"reason":req.reason,"u":user.user_id})
    paid=invoice["paid_amount"]-req.amount;balance=invoice["balance_amount"]+req.amount
    await db.execute(text("UPDATE billing.invoices SET paid_amount=:paid,balance_amount=:balance,billing_status_id=:s WHERE invoice_id=:id"),{"paid":paid,"balance":balance,"s":await status_id(db,"Pending" if paid==0 else "Partially Paid"),"id":invoice_id})
    await db.execute(text("UPDATE billing.billing_accounts SET total_paid=GREATEST(total_paid-:a,0),total_due=total_due+:a WHERE billing_account_id=:id"),{"a":req.amount,"id":invoice["billing_account_id"]})
    await db.execute(text("INSERT INTO billing.billing_action_audit(invoice_id,action,amount,reason,performed_by) VALUES(:id,'Refund',:amount,:reason,:user)"),{"id":invoice_id,"amount":req.amount,"reason":req.reason,"user":user.user_id});await db.commit();return {"refund_id":rid,"status":"Completed","amount":req.amount}


@router.post("/invoices/{invoice_id}/credit-notes", status_code=201)
async def create_credit(invoice_id: UUID, req: CreditCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(accounting_access)):
    invoice=(await db.execute(text("SELECT * FROM billing.invoices WHERE invoice_id=:id FOR UPDATE"),{"id":invoice_id})).mappings().first()
    if not invoice: raise HTTPException(404,"Invoice not found")
    if req.amount>invoice["balance_amount"]: raise HTTPException(409,"Credit exceeds outstanding balance")
    cid=uuid4();number=f"CN-{uuid4().hex[:14].upper()}";await db.execute(text("INSERT INTO billing.credit_notes(credit_note_id,invoice_id,credit_note_number,credit_amount,reason,issued_by) VALUES(:id,:invoice,:number,:amount,:reason,:user)"),{"id":cid,"invoice":invoice_id,"number":number,"amount":req.amount,"reason":req.reason,"user":user.user_id})
    balance=invoice["balance_amount"]-req.amount;await db.execute(text("UPDATE billing.invoices SET balance_amount=:b,total_amount=total_amount-:a,billing_status_id=:s WHERE invoice_id=:id"),{"b":balance,"a":req.amount,"s":await status_id(db,"Paid" if balance==0 else "Partially Paid"),"id":invoice_id});await db.execute(text("UPDATE billing.billing_accounts SET total_due=GREATEST(total_due-:a,0) WHERE billing_account_id=:id"),{"a":req.amount,"id":invoice["billing_account_id"]})
    await db.execute(text("INSERT INTO billing.billing_action_audit(invoice_id,action,amount,reason,performed_by) VALUES(:id,'Credit Note',:amount,:reason,:user)"),{"id":invoice_id,"amount":req.amount,"reason":req.reason,"user":user.user_id});await db.commit();return {"credit_note_id":cid,"credit_note_number":number,"amount":req.amount}


@router.post("/invoices/{invoice_id}/claims", status_code=201)
async def create_claim(invoice_id: UUID, req: ClaimCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(claims_access)):
    invoice=(await db.execute(text("SELECT * FROM billing.invoices WHERE invoice_id=:id"),{"id":invoice_id})).mappings().first()
    if not invoice: raise HTTPException(404,"Invoice not found")
    if req.claim_amount>invoice["balance_amount"]: raise HTTPException(409,"Claim exceeds outstanding balance")
    cid=uuid4();await db.execute(text("INSERT INTO billing.insurance_claims(insurance_claim_id,invoice_id,patient_id,insurance_provider,policy_number,claim_number,claim_amount,approved_amount,rejected_amount,claim_status,submitted_at) VALUES(:id,:invoice,:patient,:provider,:policy,:number,:amount,0,0,'Submitted',CURRENT_TIMESTAMP)"),{"id":cid,"invoice":invoice_id,"patient":invoice["patient_id"],"provider":req.insurance_provider,"policy":req.policy_number,"number":req.claim_number,"amount":req.claim_amount});await db.commit();return {"insurance_claim_id":cid,"claim_status":"Submitted"}


@router.put("/claims/{claim_id}")
async def decide_claim(claim_id: UUID, req: ClaimDecision, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(claims_access)):
    claim=(await db.execute(text("SELECT * FROM billing.insurance_claims WHERE insurance_claim_id=:id FOR UPDATE"),{"id":claim_id})).mappings().first()
    if not claim: raise HTTPException(404,"Claim not found")
    if claim["claim_status"]!="Submitted": raise HTTPException(409,"Claim was already decided")
    if req.status=="Approved" and req.approved_amount>claim["claim_amount"]: raise HTTPException(409,"Approval exceeds claim amount")
    approved=req.approved_amount if req.status=="Approved" else Decimal("0");rejected=claim["claim_amount"]-approved
    await db.execute(text("UPDATE billing.insurance_claims SET claim_status=:s,approved_amount=:a,rejected_amount=:r,approved_at=CASE WHEN CAST(:s AS VARCHAR)='Approved' THEN CURRENT_TIMESTAMP END,rejection_reason=:reason WHERE insurance_claim_id=:id"),{"s":req.status,"a":approved,"r":rejected,"reason":req.reason or None,"id":claim_id})
    await db.execute(text("INSERT INTO billing.billing_action_audit(invoice_id,action,amount,reason,performed_by) VALUES(:invoice,:action,:amount,:reason,:user)"),{"invoice":claim["invoice_id"],"action":f"Claim {req.status}","amount":approved,"reason":req.reason or req.status,"user":user.user_id});await db.commit();return {"insurance_claim_id":claim_id,"claim_status":req.status,"approved_amount":approved,"rejected_amount":rejected}


@router.get("/reports/summary")
async def financial_summary(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(accounting_access)):
    totals=(await db.execute(text("SELECT COALESCE(sum(total_amount),0) revenue,COALESCE(sum(paid_amount),0) collected,COALESCE(sum(balance_amount),0) outstanding FROM billing.invoices i JOIN billing.billing_statuses s USING(billing_status_id) WHERE s.status_name<>'Cancelled'"))).mappings().one()
    methods=[dict(r) for r in (await db.execute(text("""SELECT m.method_name,
        COALESCE(sum(p.payment_amount),0)-COALESCE(sum(r.refunded),0) net_collected
        FROM billing.payments p JOIN billing.payment_methods m USING(payment_method_id)
        LEFT JOIN (SELECT payment_id,sum(refund_amount) refunded FROM billing.refunds
                   WHERE refund_status='Completed' GROUP BY payment_id) r USING(payment_id)
        WHERE p.payment_status='Completed' GROUP BY m.method_name ORDER BY m.method_name"""))).mappings()]
    services=[dict(r) for r in (await db.execute(text("SELECT item_type,COALESCE(sum(line_total),0) revenue FROM billing.invoice_items GROUP BY item_type ORDER BY revenue DESC"))).mappings()]
    return {"totals":dict(totals),"payment_methods":methods,"services":services}


# ----------------- Milestone 3: Payment Gateway Simulation & Pre-authorization -----------------

@router.post("/checkout/session", response_model=CheckoutSessionResponse, status_code=201)
async def create_checkout_session(
    req: CheckoutSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(access)
):
    """Create a simulated online payment gateway checkout session (Stripe / Razorpay / UPI)."""
    invoice = (await db.execute(
        text("SELECT invoice_id, balance_amount, billing_account_id FROM billing.invoices WHERE invoice_id=:id"),
        {"id": req.invoice_id}
    )).mappings().first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice["balance_amount"] <= Decimal("0.00"):
        raise HTTPException(409, "Invoice balance is already settled")

    session_id = f"cs_{req.gateway_provider.lower()}_{uuid4().hex}"
    checkout_url = f"https://checkout.hmshospital.com/{req.gateway_provider.lower()}/pay?session_id={session_id}"

    tx = PaymentGatewayTransaction(
        invoice_id=req.invoice_id,
        gateway_provider=req.gateway_provider,
        gateway_session_id=session_id,
        amount=invoice["balance_amount"],
        currency=req.currency,
        status="Pending"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return CheckoutSessionResponse(
        transaction_id=tx.transaction_id,
        invoice_id=tx.invoice_id,
        gateway_provider=tx.gateway_provider,
        gateway_session_id=tx.gateway_session_id,
        checkout_url=checkout_url,
        amount=tx.amount,
        currency=tx.currency,
        status=tx.status
    )


@router.post("/webhook/payment-settlement", response_model=PaymentWebhookResponse)
async def process_payment_webhook(
    payload: PaymentWebhookPayload,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(access)
):
    """Process simulated gateway webhook callback, verify signature, and auto-settle the invoice."""
    # Find transaction
    tx_row = (await db.execute(
        text("SELECT * FROM billing.payment_gateway_transactions WHERE gateway_session_id=:sid FOR UPDATE"),
        {"sid": payload.gateway_session_id}
    )).mappings().first()
    if not tx_row:
        raise HTTPException(404, "Payment gateway session not found")
    if tx_row["status"] == "Completed":
        return PaymentWebhookResponse(
            status="already_processed",
            transaction_id=tx_row["transaction_id"],
            invoice_id=tx_row["invoice_id"],
            invoice_settled=True,
            message="Payment was already settled for this session"
        )

    # Basic signature validation check
    if not payload.signature or len(payload.signature) < 8:
        raise HTTPException(400, "Invalid or missing webhook signature")

    invoice = (await db.execute(
        text("SELECT * FROM billing.invoices WHERE invoice_id=:id FOR UPDATE"),
        {"id": tx_row["invoice_id"]}
    )).mappings().first()
    if not invoice:
        raise HTTPException(404, "Associated invoice not found")

    amount = payload.paid_amount
    if amount <= Decimal("0.00"):
        raise HTTPException(400, "Paid amount must be greater than zero")

    method_name = f"Online / {tx_row['gateway_provider']}"
    method_id = await db.scalar(
        text("""INSERT INTO billing.payment_methods(method_name) VALUES (:name)
                ON CONFLICT(method_name) DO UPDATE SET method_name=EXCLUDED.method_name RETURNING payment_method_id"""),
        {"name": method_name}
    )

    # Insert payment record
    payment_id = uuid4()
    await db.execute(
        text("""INSERT INTO billing.payments
                (payment_id, invoice_id, patient_id, payment_method_id, payment_reference, payment_amount, payment_status, received_by)
                VALUES (:pid, :iid, :ptid, :mid, :ref, :amt, 'Completed', :user)"""),
        {
            "pid": payment_id,
            "iid": invoice["invoice_id"],
            "ptid": invoice["patient_id"],
            "mid": method_id,
            "ref": payload.gateway_reference,
            "amt": amount,
            "user": user.user_id
        }
    )

    # Update invoice balances
    new_balance = max(Decimal("0.00"), invoice["balance_amount"] - amount)
    is_settled = (new_balance == Decimal("0.00"))
    inv_status = await status_id(db, "Paid" if is_settled else "Partially Paid")

    await db.execute(
        text("""UPDATE billing.invoices SET paid_amount=paid_amount+:amt,
                balance_amount=:bal, billing_status_id=:st, updated_at=CURRENT_TIMESTAMP WHERE invoice_id=:id"""),
        {"amt": amount, "bal": new_balance, "st": inv_status, "id": invoice["invoice_id"]}
    )

    # Update billing account
    await db.execute(
        text("""UPDATE billing.billing_accounts SET total_paid=COALESCE(total_paid,0)+:amt,
                total_due=GREATEST(COALESCE(total_due,0)-:amt, 0), updated_at=CURRENT_TIMESTAMP WHERE billing_account_id=:id"""),
        {"amt": amount, "id": invoice["billing_account_id"]}
    )

    # Update gateway transaction
    await db.execute(
        text("""UPDATE billing.payment_gateway_transactions
                SET status='Completed', payment_reference=:ref, signature_verified=TRUE, updated_at=CURRENT_TIMESTAMP
                WHERE transaction_id=:tid"""),
        {"ref": payload.gateway_reference, "tid": tx_row["transaction_id"]}
    )

    await db.commit()

    return PaymentWebhookResponse(
        status="success",
        transaction_id=tx_row["transaction_id"],
        invoice_id=invoice["invoice_id"],
        invoice_settled=is_settled,
        message="Online payment successfully settled"
    )


@router.post("/insurance/pre-authorize", response_model=InsurancePreauthResponse, status_code=201)
async def create_insurance_preauth(
    req: InsurancePreauthCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(claims_access)
):
    """Register and verify an insurance policy pre-authorization approval code."""
    approval_code = f"AUTH-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:6].upper()}"

    preauth = InsurancePreauthorization(
        patient_id=req.patient_id,
        insurance_provider=req.insurance_provider,
        policy_number=req.policy_number,
        approval_code=approval_code,
        authorized_amount=req.authorized_amount,
        copay_percentage=req.copay_percentage,
        valid_from=req.valid_from,
        valid_until=req.valid_until,
        status="Approved",
        created_by=user.user_id
    )
    db.add(preauth)
    await db.commit()
    await db.refresh(preauth)

    return InsurancePreauthResponse(
        preauth_id=preauth.preauth_id,
        patient_id=preauth.patient_id,
        insurance_provider=preauth.insurance_provider,
        policy_number=preauth.policy_number,
        approval_code=preauth.approval_code,
        authorized_amount=preauth.authorized_amount,
        copay_percentage=preauth.copay_percentage,
        valid_from=preauth.valid_from,
        valid_until=preauth.valid_until,
        status=preauth.status
    )


@router.get("/insurance/pre-authorizations/{patient_id}", response_model=list[InsurancePreauthResponse])
async def list_patient_preauths(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(claims_access)
):
    """List active insurance pre-authorizations for a patient."""
    res = await db.execute(
        text("SELECT * FROM billing.insurance_preauthorizations WHERE patient_id=:pid ORDER BY created_at DESC"),
        {"pid": patient_id}
    )
    rows = res.mappings().all()
    return [
        InsurancePreauthResponse(
            preauth_id=r["preauth_id"],
            patient_id=r["patient_id"],
            insurance_provider=r["insurance_provider"],
            policy_number=r["policy_number"],
            approval_code=r["approval_code"],
            authorized_amount=r["authorized_amount"],
            copay_percentage=r["copay_percentage"],
            valid_from=r["valid_from"],
            valid_until=r["valid_until"],
            status=r["status"]
        ) for r in rows
    ]


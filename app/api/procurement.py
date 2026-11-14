import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, require_roles
from app.config import get_db
from app.schemas.procurement import CancelRequest, DecisionCreate, GoodsReceiptCreate, InventoryItemUpdate, PurchaseOrderCreate, PurchaseRequestCreate, QuoteCreate, VendorCreate, VendorUpdate
from app.services.realtime import broker

router = APIRouter(prefix="/procurement", tags=["Procurement & Inventory"])
read_access = require_roles(["procurement_staff", "procurement_manager", "admin", "super_admin"])
staff_access = require_roles(["procurement_staff", "procurement_manager", "admin", "super_admin"])
manager_access = require_roles(["procurement_manager", "admin", "super_admin"])


@router.get("/events")
async def events(_user: CurrentUser = Depends(read_access)):
    return StreamingResponse(broker.stream("procurement"), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    row = (await db.execute(text("""SELECT
      (SELECT count(*) FROM inventory.purchase_requests WHERE request_status='Submitted') pending_requests,
      (SELECT count(*) FROM inventory.purchase_orders WHERE order_status IN ('Issued','Partially Received')) open_orders,
      (SELECT count(*) FROM inventory.inventory_stock s JOIN inventory.inventory_items i USING(inventory_item_id)
         WHERE COALESCE(s.available_stock_quantity,0)<=COALESCE(i.reorder_level,0)) low_stock_items,
      (SELECT count(*) FROM inventory.vendors) vendors"""))).mappings().one()
    return dict(row)


@router.get("/items")
async def items(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    rows = await db.execute(text("""SELECT i.inventory_item_id,i.item_code,i.item_name,i.item_type,i.reorder_level,u.unit_code,
      COALESCE(sum(s.available_stock_quantity),0) available_stock
      FROM inventory.inventory_items i LEFT JOIN inventory.inventory_units_of_measure u USING(unit_of_measure_id)
      LEFT JOIN inventory.inventory_stock s USING(inventory_item_id)
      WHERE i.is_active GROUP BY i.inventory_item_id,u.unit_code ORDER BY i.item_name"""))
    return [dict(row) for row in rows.mappings()]


@router.get("/vendors")
async def vendors(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    rows = await db.execute(text("SELECT * FROM inventory.vendors WHERE is_active ORDER BY vendor_name"))
    return [dict(row) for row in rows.mappings()]


@router.post("/vendors", status_code=201)
async def create_vendor(req: VendorCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    vendor_id=uuid.uuid4()
    try:
        await db.execute(text("""INSERT INTO inventory.vendors(vendor_id,vendor_code,vendor_name,vendor_type,contact_email,contact_phone,vendor_address,updated_at,updated_by)
          VALUES(:id,:vendor_code,:vendor_name,:vendor_type,:contact_email,:contact_phone,:vendor_address,:now,:user)"""),{"id":vendor_id,**req.model_dump(),"now":datetime.utcnow(),"user":user.user_id})
        await db.commit()
    except Exception:
        await db.rollback(); raise HTTPException(409,"Vendor code already exists")
    await broker.publish("procurement","vendor.created",{"vendor_id":vendor_id}); return {"vendor_id":vendor_id}


@router.patch("/vendors/{vendor_id}")
async def update_vendor(vendor_id: uuid.UUID, req: VendorUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    values=req.model_dump(exclude_unset=True)
    if not values: return {"status":"Unchanged"}
    sets=",".join(f"{key}=:{key}" for key in values)
    result=await db.execute(text(f"UPDATE inventory.vendors SET {sets},updated_at=:now,updated_by=:user WHERE vendor_id=:id AND is_active"),{**values,"now":datetime.utcnow(),"user":user.user_id,"id":vendor_id})
    if result.rowcount!=1: raise HTTPException(404,"Active vendor not found")
    await db.commit(); await broker.publish("procurement","vendor.updated",{"vendor_id":vendor_id}); return {"status":"Updated"}


@router.delete("/vendors/{vendor_id}")
async def archive_vendor(vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    open_orders=await db.scalar(text("SELECT count(*) FROM inventory.purchase_orders WHERE vendor_id=:id AND order_status IN ('Issued','Partially Received')"),{"id":vendor_id})
    if open_orders: raise HTTPException(409,"Vendor has open purchase orders")
    result=await db.execute(text("UPDATE inventory.vendors SET is_active=FALSE,updated_at=:now,updated_by=:user WHERE vendor_id=:id AND is_active"),{"now":datetime.utcnow(),"user":user.user_id,"id":vendor_id})
    if result.rowcount!=1: raise HTTPException(404,"Active vendor not found")
    await db.commit(); await broker.publish("procurement","vendor.archived",{"vendor_id":vendor_id}); return {"status":"Archived"}


@router.patch("/items/{item_id}")
async def update_item(item_id: uuid.UUID, req: InventoryItemUpdate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    values=req.model_dump(exclude_unset=True)
    if not values: return {"status":"Unchanged"}
    sets=",".join(f"{key}=:{key}" for key in values)
    result=await db.execute(text(f"UPDATE inventory.inventory_items SET {sets},updated_at=:now,updated_by=:user WHERE inventory_item_id=:id AND is_active"),{**values,"now":datetime.utcnow(),"user":user.user_id,"id":item_id})
    if result.rowcount!=1: raise HTTPException(404,"Active item not found")
    await db.commit(); await broker.publish("procurement","item.updated",{"item_id":item_id}); return {"status":"Updated"}


@router.get("/warehouses")
async def warehouses(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    rows = await db.execute(text("SELECT * FROM inventory.warehouses ORDER BY warehouse_name"))
    return [dict(row) for row in rows.mappings()]


@router.get("/requests")
async def requests(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    rows = await db.execute(text("""SELECT r.*,
      COALESCE((SELECT sum(x.requested_quantity*COALESCE(x.estimated_unit_price,0)) FROM inventory.purchase_request_items x WHERE x.purchase_request_id=r.purchase_request_id),0) estimated_total,
      (SELECT count(*) FROM inventory.purchase_request_items x WHERE x.purchase_request_id=r.purchase_request_id) item_count,
      (SELECT count(*) FROM inventory.vendor_quotes q WHERE q.purchase_request_id=r.purchase_request_id) quote_count
      FROM inventory.purchase_requests r ORDER BY r.request_date DESC"""))
    return [dict(row) for row in rows.mappings()]


@router.get("/requests/{request_id}")
async def request_detail(request_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    request = (await db.execute(text("SELECT * FROM inventory.purchase_requests WHERE purchase_request_id=:id"), {"id": request_id})).mappings().first()
    if not request:
        raise HTTPException(404, "Purchase request not found")
    request_items = await db.execute(text("""SELECT x.*,i.item_code,i.item_name FROM inventory.purchase_request_items x
      JOIN inventory.inventory_items i USING(inventory_item_id) WHERE x.purchase_request_id=:id"""), {"id": request_id})
    quotes = await db.execute(text("""SELECT q.*,v.vendor_name FROM inventory.vendor_quotes q JOIN inventory.vendors v USING(vendor_id)
      WHERE q.purchase_request_id=:id ORDER BY q.quoted_amount,q.delivery_days"""), {"id": request_id})
    return {"request": dict(request), "items": [dict(r) for r in request_items.mappings()], "quotes": [dict(r) for r in quotes.mappings()]}


@router.post("/requests", status_code=201)
async def create_request(req: PurchaseRequestCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(staff_access)):
    item_ids = [item.inventory_item_id for item in req.items]
    found = (await db.execute(text("SELECT inventory_item_id FROM inventory.inventory_items WHERE inventory_item_id=ANY(:ids)"), {"ids": item_ids})).scalars().all()
    if len(set(found)) != len(set(item_ids)):
        raise HTTPException(404, "One or more inventory items were not found")
    request_id = uuid.uuid4()
    number = f"PR-{datetime.utcnow():%Y%m%d}-{str(request_id)[:8].upper()}"
    await db.execute(text("""INSERT INTO inventory.purchase_requests
      (purchase_request_id,requested_by,request_date,request_status,request_notes,request_number,requested_department,required_by)
      VALUES(:id,:user,:now,'Submitted',:notes,:number,:department,:required_by)"""),
      {"id": request_id, "user": user.user_id, "now": datetime.utcnow(), "notes": req.request_notes,
       "number": number, "department": req.requested_department, "required_by": req.required_by})
    for item in req.items:
        await db.execute(text("""INSERT INTO inventory.purchase_request_items
          (purchase_request_id,inventory_item_id,requested_quantity,estimated_unit_price,justification)
          VALUES(:request,:item,:quantity,:price,:justification)"""),
          {"request": request_id, "item": item.inventory_item_id, "quantity": item.requested_quantity,
           "price": item.estimated_unit_price, "justification": item.justification})
    await db.commit(); await broker.publish("procurement","request.created",{"request_id":request_id})
    return {"purchase_request_id": request_id, "request_number": number, "status": "Submitted"}


@router.post("/requests/{request_id}/cancel")
async def cancel_request(request_id: uuid.UUID, req: CancelRequest, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    result=await db.execute(text("""UPDATE inventory.purchase_requests SET request_status='Cancelled',cancellation_reason=:reason,updated_at=:now,updated_by=:user
      WHERE purchase_request_id=:id AND request_status IN ('Submitted','Approved')"""),{"reason":req.reason,"now":datetime.utcnow(),"user":user.user_id,"id":request_id})
    if result.rowcount!=1: raise HTTPException(409,"Request is missing or cannot be cancelled after ordering")
    await db.commit(); await broker.publish("procurement","request.cancelled",{"request_id":request_id}); return {"status":"Cancelled"}


@router.post("/requests/{request_id}/decision")
async def decide_request(request_id: uuid.UUID, req: DecisionCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    request = (await db.execute(text("SELECT * FROM inventory.purchase_requests WHERE purchase_request_id=:id FOR UPDATE"), {"id": request_id})).mappings().first()
    if not request:
        raise HTTPException(404, "Purchase request not found")
    if request["request_status"] != "Submitted":
        raise HTTPException(409, "Only submitted requests can be decided")
    status = "Approved" if req.approved else "Rejected"
    notes = "\n".join(part for part in (request["request_notes"], req.notes) if part)
    await db.execute(text("UPDATE inventory.purchase_requests SET request_status=:status,request_notes=:notes WHERE purchase_request_id=:id"), {"status": status, "notes": notes or None, "id": request_id})
    if req.approved:
        requisition_id = uuid.uuid4()
        await db.execute(text("""INSERT INTO inventory.purchase_requisitions
          (purchase_requisition_id,purchase_request_id,requisition_number,requisition_status,approved_by,approved_at)
          VALUES(:id,:request,:number,'Approved',:user,:now)"""), {"id": requisition_id, "request": request_id,
          "number": request["request_number"].replace("PR-", "REQ-"), "user": user.user_id, "now": datetime.utcnow()})
    await db.commit(); await broker.publish("procurement","request.decided",{"request_id":request_id,"status":status})
    return {"purchase_request_id": request_id, "status": status}


@router.post("/requests/{request_id}/quotes", status_code=201)
async def add_quote(request_id: uuid.UUID, req: QuoteCreate, db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(staff_access)):
    status = await db.scalar(text("SELECT request_status FROM inventory.purchase_requests WHERE purchase_request_id=:id"), {"id": request_id})
    if status != "Approved":
        raise HTTPException(409, "Request must be approved before collecting quotations")
    if not await db.scalar(text("SELECT 1 FROM inventory.vendors WHERE vendor_id=:id"), {"id": req.vendor_id}):
        raise HTTPException(404, "Vendor not found")
    quote_id = uuid.uuid4()
    await db.execute(text("""INSERT INTO inventory.vendor_quotes
      (vendor_quote_id,purchase_request_id,vendor_id,quote_number,quoted_amount,delivery_days,quote_notes)
      VALUES(:id,:request,:vendor,:number,:amount,:days,:notes)"""), {"id": quote_id, "request": request_id,
      "vendor": req.vendor_id, "number": req.quote_number, "amount": req.quoted_amount, "days": req.delivery_days, "notes": req.quote_notes})
    await db.commit(); await broker.publish("procurement","quote.created",{"request_id":request_id,"quote_id":quote_id})
    return {"vendor_quote_id": quote_id, "status": "Submitted"}


@router.post("/requests/{request_id}/purchase-order", status_code=201)
async def create_order(request_id: uuid.UUID, req: PurchaseOrderCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(manager_access)):
    quote = (await db.execute(text("SELECT * FROM inventory.vendor_quotes WHERE vendor_quote_id=:quote AND purchase_request_id=:request"), {"quote": req.vendor_quote_id, "request": request_id})).mappings().first()
    if not quote:
        raise HTTPException(404, "Quotation not found for this request")
    requisition = await db.scalar(text("SELECT purchase_requisition_id FROM inventory.purchase_requisitions WHERE purchase_request_id=:id AND requisition_status='Approved'"), {"id": request_id})
    if not requisition:
        raise HTTPException(409, "Approved requisition not found")
    order_id = uuid.uuid4(); number = f"PO-{date.today():%Y%m%d}-{str(order_id)[:8].upper()}"
    await db.execute(text("""INSERT INTO inventory.purchase_orders
      (purchase_order_id,vendor_id,purchase_requisition_id,purchase_order_number,order_date,expected_delivery_date,order_status,total_order_amount)
      VALUES(:id,:vendor,:requisition,:number,CURRENT_DATE,:delivery,'Issued',:total)"""), {"id": order_id, "vendor": quote["vendor_id"],
      "requisition": requisition, "number": number, "delivery": req.expected_delivery_date, "total": quote["quoted_amount"]})
    request_items = (await db.execute(text("SELECT * FROM inventory.purchase_request_items WHERE purchase_request_id=:id"), {"id": request_id})).mappings().all()
    total_quantity = sum(item["requested_quantity"] for item in request_items)
    for item in request_items:
        unit_price = quote["quoted_amount"] / total_quantity if total_quantity else 0
        await db.execute(text("""INSERT INTO inventory.purchase_order_items
          (purchase_order_id,inventory_item_id,ordered_quantity,unit_price,total_price)
          VALUES(:order,:item,:quantity,:price,:total)"""), {"order": order_id, "item": item["inventory_item_id"],
          "quantity": item["requested_quantity"], "price": unit_price, "total": unit_price * item["requested_quantity"]})
    await db.execute(text("UPDATE inventory.vendor_quotes SET quote_status=CASE WHEN vendor_quote_id=:quote THEN 'Selected' ELSE 'Not Selected' END WHERE purchase_request_id=:request"), {"quote": req.vendor_quote_id, "request": request_id})
    await db.execute(text("UPDATE inventory.purchase_requests SET request_status='Ordered' WHERE purchase_request_id=:id"), {"id": request_id})
    await db.execute(text("INSERT INTO inventory.procurement_approvals(purchase_order_id,approval_level,approved_by,approval_status,approved_at) VALUES(:order,'Manager',:user,'Approved',:now)"), {"order": order_id, "user": user.user_id, "now": datetime.utcnow()})
    await db.commit(); await broker.publish("procurement","order.created",{"request_id":request_id,"order_id":order_id})
    return {"purchase_order_id": order_id, "purchase_order_number": number, "status": "Issued"}


@router.get("/orders")
async def orders(db: AsyncSession = Depends(get_db), _user: CurrentUser = Depends(read_access)):
    rows = await db.execute(text("""SELECT p.*,v.vendor_name FROM inventory.purchase_orders p
      JOIN inventory.vendors v USING(vendor_id) ORDER BY p.order_date DESC,p.created_at DESC"""))
    return [dict(row) for row in rows.mappings()]


@router.post("/orders/{order_id}/receipt", status_code=201)
async def receive_order(order_id: uuid.UUID, req: GoodsReceiptCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = Depends(staff_access)):
    order = (await db.execute(text("SELECT * FROM inventory.purchase_orders WHERE purchase_order_id=:id FOR UPDATE"), {"id": order_id})).mappings().first()
    if not order:
        raise HTTPException(404, "Purchase order not found")
    if order["order_status"] not in ("Issued", "Partially Received"):
        raise HTTPException(409, "Purchase order cannot receive goods in its current state")
    if not await db.scalar(text("SELECT 1 FROM inventory.warehouses WHERE warehouse_id=:id"), {"id": req.warehouse_id}):
        raise HTTPException(404, "Warehouse not found")
    ordered = {row[0]: row[1] for row in (await db.execute(text("SELECT inventory_item_id,ordered_quantity FROM inventory.purchase_order_items WHERE purchase_order_id=:id"), {"id": order_id})).all()}
    if any(item.inventory_item_id not in ordered or item.received_quantity > ordered[item.inventory_item_id] for item in req.items):
        raise HTTPException(422, "Receipt contains an item or quantity outside the purchase order")
    receipt_id = uuid.uuid4(); number = f"GRN-{date.today():%Y%m%d}-{str(receipt_id)[:8].upper()}"
    await db.execute(text("""INSERT INTO inventory.goods_receipts(goods_receipt_id,purchase_order_id,receipt_number,received_by,received_date,receipt_status)
      VALUES(:id,:order,:number,:user,:now,'Accepted')"""), {"id": receipt_id, "order": order_id, "number": number, "user": user.user_id, "now": datetime.utcnow()})
    for item in req.items:
        await db.execute(text("""INSERT INTO inventory.goods_receipt_items(goods_receipt_id,inventory_item_id,received_quantity,accepted_quantity,rejected_quantity)
          VALUES(:receipt,:item,:received,:accepted,:rejected)"""), {"receipt": receipt_id, "item": item.inventory_item_id,
          "received": item.received_quantity, "accepted": item.accepted_quantity, "rejected": item.rejected_quantity})
        stock_id = await db.scalar(text("SELECT inventory_stock_id FROM inventory.inventory_stock WHERE inventory_item_id=:item AND warehouse_id=:warehouse FOR UPDATE"), {"item": item.inventory_item_id, "warehouse": req.warehouse_id})
        if not stock_id:
            stock_id = uuid.uuid4()
            await db.execute(text("""INSERT INTO inventory.inventory_stock(inventory_stock_id,inventory_item_id,warehouse_id,current_stock_quantity,reserved_stock_quantity,available_stock_quantity)
              VALUES(:id,:item,:warehouse,:quantity,0,:quantity)"""), {"id": stock_id, "item": item.inventory_item_id, "warehouse": req.warehouse_id, "quantity": item.accepted_quantity})
        else:
            await db.execute(text("UPDATE inventory.inventory_stock SET current_stock_quantity=COALESCE(current_stock_quantity,0)+:quantity,available_stock_quantity=COALESCE(available_stock_quantity,0)+:quantity WHERE inventory_stock_id=:id"), {"quantity": item.accepted_quantity, "id": stock_id})
        await db.execute(text("INSERT INTO inventory.inventory_stock_movements(inventory_stock_id,movement_type,movement_quantity,destination_location,moved_at) VALUES(:stock,'Goods Receipt',:quantity,:warehouse,:now)"), {"stock": stock_id, "quantity": item.accepted_quantity, "warehouse": str(req.warehouse_id), "now": datetime.utcnow()})
    await db.execute(text("UPDATE inventory.purchase_orders SET order_status='Received' WHERE purchase_order_id=:id"), {"id": order_id})
    await db.commit(); await broker.publish("procurement","receipt.created",{"order_id":order_id,"receipt_id":receipt_id})
    return {"goods_receipt_id": receipt_id, "receipt_number": number, "status": "Accepted"}

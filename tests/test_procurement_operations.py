import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import CurrentUser, get_current_user
from app.config import get_db, settings
from main import app


@pytest.fixture
async def procurement_client():
    engine = create_async_engine(settings.database_url)
    connection = await engine.connect(); transaction = await connection.begin()
    session = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)()
    async def db_override(): yield session
    async def user_override():
        return CurrentUser(user_id=uuid.uuid4(), employee_id=None, patient_id=None, username="PROC-TEST", roles=["procurement_manager"], name="Procurement Test")
    app.dependency_overrides[get_db]=db_override; app.dependency_overrides[get_current_user]=user_override
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as client: yield client,session
    app.dependency_overrides.clear(); await session.close(); await transaction.rollback(); await connection.close(); await engine.dispose()


@pytest.mark.asyncio
async def test_requisition_quote_order_receipt_updates_stock(procurement_client):
    client,db=procurement_client
    item=await db.scalar(text("SELECT inventory_item_id FROM inventory.inventory_items LIMIT 1"))
    vendor=await db.scalar(text("SELECT vendor_id FROM inventory.vendors LIMIT 1"))
    warehouse=await db.scalar(text("SELECT warehouse_id FROM inventory.warehouses LIMIT 1"))
    assert item and vendor and warehouse
    created=await client.post('/api/v1/procurement/requests',json={"requested_department":"Emergency","required_by":str(date.today()+timedelta(days=7)),"request_notes":"Urgent stock","items":[{"inventory_item_id":str(item),"requested_quantity":10,"estimated_unit_price":25,"justification":"Below reorder level"}]})
    assert created.status_code==201,created.text; request_id=created.json()['purchase_request_id']
    decision=await client.post(f'/api/v1/procurement/requests/{request_id}/decision',json={"approved":True,"notes":"Budget approved"})
    assert decision.status_code==200,decision.text
    quote=await client.post(f'/api/v1/procurement/requests/{request_id}/quotes',json={"vendor_id":str(vendor),"quote_number":"Q-TEST-01","quoted_amount":250,"delivery_days":5})
    assert quote.status_code==201,quote.text
    order=await client.post(f'/api/v1/procurement/requests/{request_id}/purchase-order',json={"vendor_quote_id":quote.json()['vendor_quote_id'],"expected_delivery_date":str(date.today()+timedelta(days=5))})
    assert order.status_code==201,order.text; order_id=order.json()['purchase_order_id']
    before=await db.scalar(text("SELECT COALESCE(sum(available_stock_quantity),0) FROM inventory.inventory_stock WHERE inventory_item_id=:id"),{"id":item})
    receipt=await client.post(f'/api/v1/procurement/orders/{order_id}/receipt',json={"warehouse_id":str(warehouse),"items":[{"inventory_item_id":str(item),"received_quantity":10,"accepted_quantity":9,"rejected_quantity":1}]})
    assert receipt.status_code==201,receipt.text
    after=await db.scalar(text("SELECT COALESCE(sum(available_stock_quantity),0) FROM inventory.inventory_stock WHERE inventory_item_id=:id"),{"id":item})
    assert after==before+9

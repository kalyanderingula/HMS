BEGIN;

INSERT INTO security.roles(role_name) VALUES ('procurement_staff'), ('procurement_manager')
ON CONFLICT(role_name) DO NOTHING;

ALTER TABLE inventory.purchase_requests
    ADD COLUMN IF NOT EXISTS request_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS requested_department VARCHAR(255),
    ADD COLUMN IF NOT EXISTS required_by DATE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_purchase_request_number
    ON inventory.purchase_requests(request_number) WHERE request_number IS NOT NULL;

CREATE TABLE IF NOT EXISTS inventory.purchase_request_items (
    purchase_request_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_request_id UUID NOT NULL REFERENCES inventory.purchase_requests(purchase_request_id) ON DELETE CASCADE,
    inventory_item_id UUID NOT NULL REFERENCES inventory.inventory_items(inventory_item_id),
    requested_quantity NUMERIC(14,2) NOT NULL CHECK (requested_quantity > 0),
    estimated_unit_price NUMERIC(14,2) CHECK (estimated_unit_price >= 0),
    justification TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory.vendor_quotes (
    vendor_quote_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_request_id UUID NOT NULL REFERENCES inventory.purchase_requests(purchase_request_id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES inventory.vendors(vendor_id),
    quote_number VARCHAR(100) NOT NULL,
    quoted_amount NUMERIC(14,2) NOT NULL CHECK (quoted_amount >= 0),
    delivery_days INT CHECK (delivery_days >= 0),
    quote_status VARCHAR(100) DEFAULT 'Submitted',
    quote_notes TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (purchase_request_id, vendor_id, quote_number)
);

CREATE INDEX IF NOT EXISTS idx_purchase_requests_status_date
    ON inventory.purchase_requests(request_status, request_date DESC);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_status_date
    ON inventory.purchase_orders(order_status, order_date DESC);

INSERT INTO inventory.inventory_categories(category_code,category_name,description)
VALUES ('MED-SUP','Medical Supplies','General clinical consumables'),
       ('OFF-SUP','Office Supplies','Administrative supplies')
ON CONFLICT(category_code) DO NOTHING;

INSERT INTO inventory.inventory_subcategories(inventory_category_id,subcategory_code,subcategory_name)
SELECT inventory_category_id,'PPE','Personal Protective Equipment'
FROM inventory.inventory_categories WHERE category_code='MED-SUP'
ON CONFLICT(subcategory_code) DO NOTHING;

INSERT INTO inventory.inventory_units_of_measure(unit_code,unit_name)
VALUES ('BOX','Box'),('EA','Each') ON CONFLICT(unit_code) DO NOTHING;

INSERT INTO inventory.inventory_items(inventory_subcategory_id,item_code,item_name,item_type,unit_of_measure_id,reorder_level,minimum_stock_level,maximum_stock_level)
SELECT s.inventory_subcategory_id,'PPE-GLOVE-01','Examination Gloves','Consumable',u.unit_of_measure_id,20,10,200
FROM inventory.inventory_subcategories s CROSS JOIN inventory.inventory_units_of_measure u
WHERE s.subcategory_code='PPE' AND u.unit_code='BOX'
ON CONFLICT(item_code) DO NOTHING;

INSERT INTO inventory.warehouses(warehouse_code,warehouse_name,warehouse_type,warehouse_address)
VALUES ('MAIN-WH','Central Medical Store','Central','Main Hospital Campus')
ON CONFLICT(warehouse_code) DO NOTHING;

INSERT INTO inventory.vendors(vendor_code,vendor_name,vendor_type,contact_email,contact_phone,vendor_address)
VALUES ('VEND-MED-01','HMS Medical Supplies','Medical Supplies','orders@example.invalid','0000000000','Local procurement seed')
ON CONFLICT(vendor_code) DO NOTHING;

COMMIT;

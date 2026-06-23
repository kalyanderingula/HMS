-- ==========================================
-- DIETETICS & NUTRITION MANAGEMENT
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS dietetics;

CREATE TABLE dietetics.diet_types (
    diet_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO dietetics.diet_types (type_name) VALUES
('Regular'), ('Diabetic'), ('Renal'), ('Cardiac'), ('Liquid'), ('Soft'), ('NPO');

CREATE TABLE dietetics.meal_types (
    meal_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO dietetics.meal_types (type_name) VALUES
('Breakfast'), ('Lunch'), ('Dinner'), ('Snack');

CREATE TABLE dietetics.allergen_types (
    allergen_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allergen_name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO dietetics.allergen_types (allergen_name) VALUES
('Gluten'), ('Dairy'), ('Nuts'), ('Shellfish'), ('Eggs'), ('Soy');

CREATE TABLE dietetics.patient_diet_orders (
    diet_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    admission_id UUID,
    diet_type_id UUID REFERENCES dietetics.diet_types(diet_type_id),
    ordered_by UUID NOT NULL,
    special_instructions TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.diet_plan_items (
    plan_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    diet_order_id UUID NOT NULL REFERENCES dietetics.patient_diet_orders(diet_order_id),
    meal_type_id UUID REFERENCES dietetics.meal_types(meal_type_id),
    food_item VARCHAR(255) NOT NULL,
    portion_size VARCHAR(50),
    calories INT,
    protein_g DECIMAL(6,2),
    carbs_g DECIMAL(6,2),
    fat_g DECIMAL(6,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.nutritional_assessments (
    assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    assessed_by UUID NOT NULL,
    assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    height_cm DECIMAL(5,2),
    weight_kg DECIMAL(5,2),
    bmi DECIMAL(5,2),
    caloric_needs INT,
    protein_needs_g DECIMAL(6,2),
    findings TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.nutritional_screening (
    screening_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    screening_tool VARCHAR(50) NOT NULL,
    score INT,
    risk_level VARCHAR(20),
    screened_by UUID,
    screening_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.meal_orders (
    meal_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    patient_id UUID NOT NULL,
    diet_order_id UUID REFERENCES dietetics.patient_diet_orders(diet_order_id),
    meal_type_id UUID REFERENCES dietetics.meal_types(meal_type_id),
    meal_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.meal_intake_records (
    intake_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_order_id UUID NOT NULL REFERENCES dietetics.meal_orders(meal_order_id),
    percentage_consumed INT,
    notes TEXT,
    recorded_by UUID,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.kitchen_menu (
    menu_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    diet_type_id UUID REFERENCES dietetics.diet_types(diet_type_id),
    meal_type_id UUID REFERENCES dietetics.meal_types(meal_type_id),
    menu_date DATE NOT NULL,
    items TEXT NOT NULL,
    calories INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dietetics.food_safety_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    inspection_date TIMESTAMP NOT NULL,
    inspector_name VARCHAR(255),
    area_inspected VARCHAR(255),
    temperature_check BOOLEAN,
    hygiene_score INT,
    findings TEXT,
    corrective_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_diet_orders_patient ON dietetics.patient_diet_orders(patient_id);
CREATE INDEX idx_diet_orders_admission ON dietetics.patient_diet_orders(admission_id);
CREATE INDEX idx_diet_orders_status ON dietetics.patient_diet_orders(status);
CREATE INDEX idx_diet_orders_type ON dietetics.patient_diet_orders(diet_type_id);
CREATE INDEX idx_diet_plan_items_order ON dietetics.diet_plan_items(diet_order_id);
CREATE INDEX idx_nutritional_assessments_patient ON dietetics.nutritional_assessments(patient_id);
CREATE INDEX idx_nutritional_screening_patient ON dietetics.nutritional_screening(patient_id);
CREATE INDEX idx_meal_orders_patient ON dietetics.meal_orders(patient_id);
CREATE INDEX idx_meal_orders_date ON dietetics.meal_orders(meal_date);
CREATE INDEX idx_meal_orders_status ON dietetics.meal_orders(status);
CREATE INDEX idx_meal_intake_order ON dietetics.meal_intake_records(meal_order_id);
CREATE INDEX idx_kitchen_menu_date ON dietetics.kitchen_menu(menu_date);
CREATE INDEX idx_kitchen_menu_diet_type ON dietetics.kitchen_menu(diet_type_id);

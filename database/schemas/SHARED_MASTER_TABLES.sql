-- ==========================================
-- SHARED MASTER TABLES
-- Enterprise Hospital Management System
-- ==========================================

CREATE SCHEMA IF NOT EXISTS core;

-- Buildings
CREATE TABLE core.buildings (
    building_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    building_code VARCHAR(100) UNIQUE NOT NULL,
    building_name VARCHAR(255) NOT NULL,
    address TEXT,
    total_floors INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Floors
CREATE TABLE core.floors (
    floor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    building_id UUID NOT NULL REFERENCES core.buildings(building_id),
    floor_number INT NOT NULL,
    floor_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notification Channels
CREATE TABLE core.notification_channels (
    channel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_name VARCHAR(50) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO core.notification_channels (channel_name) VALUES
('SMS'), ('Email'), ('WhatsApp'), ('Push'), ('In-App');

-- Notification Templates
CREATE TABLE core.notification_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    template_name VARCHAR(255) NOT NULL,
    channel_id UUID REFERENCES core.notification_channels(channel_id),
    subject VARCHAR(500),
    body_template TEXT NOT NULL,
    module VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notifications
CREATE TABLE core.notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    channel_id UUID REFERENCES core.notification_channels(channel_id),
    template_id UUID REFERENCES core.notification_templates(template_id),
    recipient_id UUID,
    recipient_type VARCHAR(50),
    source_module VARCHAR(100) NOT NULL,
    source_reference_id UUID,
    subject VARCHAR(500),
    body TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hospital Service Categories
CREATE TABLE core.hospital_service_categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO core.hospital_service_categories (category_name) VALUES
('Consultation'), ('Diagnostics'), ('Procedure'), ('Therapy'), ('Pharmacy');

-- Hospital Services
CREATE TABLE core.hospital_services (
    service_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    category_id UUID REFERENCES core.hospital_service_categories(category_id),
    service_code VARCHAR(100) UNIQUE NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    department_id UUID,
    base_price DECIMAL(12,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Master Document Types
CREATE TABLE core.master_document_types (
    document_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    applicable_to VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Master Languages
CREATE TABLE core.master_languages (
    language_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language_name VARCHAR(100) UNIQUE NOT NULL,
    language_code VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_buildings_tenant ON core.buildings(tenant_id);
CREATE INDEX idx_buildings_code ON core.buildings(building_code);
CREATE INDEX idx_floors_building ON core.floors(building_id);
CREATE INDEX idx_notifications_recipient ON core.notifications(recipient_id);
CREATE INDEX idx_notifications_source_module ON core.notifications(source_module);
CREATE INDEX idx_notifications_source_ref ON core.notifications(source_reference_id);
CREATE INDEX idx_notifications_status ON core.notifications(status);
CREATE INDEX idx_notification_templates_module ON core.notification_templates(module);
CREATE INDEX idx_hospital_services_category ON core.hospital_services(category_id);
CREATE INDEX idx_hospital_services_department ON core.hospital_services(department_id);
CREATE INDEX idx_hospital_services_code ON core.hospital_services(service_code);

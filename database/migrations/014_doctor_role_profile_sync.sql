BEGIN;

INSERT INTO doctor.doctor_statuses (status_name)
SELECT 'Active'
WHERE NOT EXISTS (SELECT 1 FROM doctor.doctor_statuses WHERE lower(status_name)='active');

INSERT INTO doctor.doctors (
    doctor_code, employee_id, first_name, middle_name, last_name,
    email, phone, department_id, sub_department_id, status_id,
    joining_date, created_at, updated_at
)
SELECT
    e.employee_number, e.employee_id, e.first_name, e.middle_name, e.last_name,
    e.official_email, e.official_phone, e.department_id, e.sub_department_id,
    (SELECT status_id FROM doctor.doctor_statuses WHERE lower(status_name)='active' ORDER BY status_id LIMIT 1),
    e.date_of_joining, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM human_resources.employees e
JOIN security.users u ON u.employee_id=e.employee_id
JOIN security.user_roles ur ON ur.user_id=u.user_id
JOIN security.roles r ON r.role_id=ur.role_id
WHERE r.role_name IN ('doctor','surgeon','telemedicine_doctor')
  AND NOT EXISTS (SELECT 1 FROM doctor.doctors d WHERE d.employee_id=e.employee_id)
ON CONFLICT (doctor_code) DO NOTHING;

CREATE OR REPLACE FUNCTION doctor.sync_profile_from_clinical_role()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    clinical_role TEXT;
    employee_record human_resources.employees%ROWTYPE;
BEGIN
    SELECT role_name INTO clinical_role FROM security.roles WHERE role_id=NEW.role_id;
    IF clinical_role NOT IN ('doctor','surgeon','telemedicine_doctor') THEN
        RETURN NEW;
    END IF;
    SELECT e.* INTO employee_record
    FROM security.users u JOIN human_resources.employees e ON e.employee_id=u.employee_id
    WHERE u.user_id=NEW.user_id;
    IF employee_record.employee_id IS NULL THEN RETURN NEW; END IF;
    INSERT INTO doctor.doctors (
        doctor_code,employee_id,first_name,middle_name,last_name,email,phone,
        department_id,sub_department_id,status_id,joining_date,created_at,updated_at
    ) VALUES (
        employee_record.employee_number,employee_record.employee_id,employee_record.first_name,
        employee_record.middle_name,employee_record.last_name,employee_record.official_email,
        employee_record.official_phone,employee_record.department_id,employee_record.sub_department_id,
        (SELECT status_id FROM doctor.doctor_statuses WHERE lower(status_name)='active' ORDER BY status_id LIMIT 1),
        employee_record.date_of_joining,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
    ) ON CONFLICT (doctor_code) DO UPDATE SET
        employee_id=EXCLUDED.employee_id,first_name=EXCLUDED.first_name,middle_name=EXCLUDED.middle_name,
        last_name=EXCLUDED.last_name,email=EXCLUDED.email,phone=EXCLUDED.phone,updated_at=CURRENT_TIMESTAMP;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_sync_doctor_profile ON security.user_roles;
CREATE TRIGGER trg_sync_doctor_profile
AFTER INSERT OR UPDATE OF role_id ON security.user_roles
FOR EACH ROW EXECUTE FUNCTION doctor.sync_profile_from_clinical_role();

COMMIT;

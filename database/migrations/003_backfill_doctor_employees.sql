BEGIN;

INSERT INTO doctor.doctor_statuses (status_name)
SELECT 'Active'
WHERE NOT EXISTS (
    SELECT 1 FROM doctor.doctor_statuses WHERE lower(status_name) = 'active'
);

INSERT INTO doctor.doctors (
    doctor_code, employee_id, first_name, middle_name, last_name,
    email, phone, department_id, sub_department_id, status_id,
    joining_date, created_at, updated_at
)
SELECT
    e.employee_number, e.employee_id, e.first_name, e.middle_name, e.last_name,
    e.official_email, e.official_phone, e.department_id, e.sub_department_id,
    (SELECT status_id FROM doctor.doctor_statuses WHERE lower(status_name) = 'active' ORDER BY status_id LIMIT 1),
    e.date_of_joining, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
FROM human_resources.employees e
JOIN security.users u ON u.employee_id = e.employee_id
JOIN security.user_roles ur ON ur.user_id = u.user_id
JOIN security.roles r ON r.role_id = ur.role_id
WHERE r.role_name IN ('doctor', 'surgeon', 'telemedicine_doctor')
  AND NOT EXISTS (
      SELECT 1 FROM doctor.doctors d WHERE d.employee_id = e.employee_id
  )
ON CONFLICT (doctor_code) DO NOTHING;

COMMIT;

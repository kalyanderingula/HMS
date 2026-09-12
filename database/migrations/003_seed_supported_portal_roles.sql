INSERT INTO security.roles (role_name) VALUES
('super_admin'), ('admin'), ('hr_manager'),
('doctor'), ('telemedicine_doctor'),
('surgeon'), ('ot_nurse'), ('anesthesiologist'),
('nurse'), ('icu_staff'), ('receptionist'),
('pharmacist'), ('lab_technician'), ('radiologist'),
('accountant'), ('insurance_officer'),
('blood_bank_technician'), ('emergency_staff')
ON CONFLICT (role_name) DO NOTHING;

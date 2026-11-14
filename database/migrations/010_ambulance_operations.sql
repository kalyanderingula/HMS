BEGIN;

INSERT INTO security.roles(role_name) VALUES ('ambulance_staff')
ON CONFLICT(role_name) DO NOTHING;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_ambulance_dispatch_patient'
          AND conrelid = 'ambulance.emergency_dispatch_requests'::regclass
    ) THEN
        ALTER TABLE ambulance.emergency_dispatch_requests
            ADD CONSTRAINT fk_ambulance_dispatch_patient
            FOREIGN KEY (patient_id) REFERENCES patient.patients(patient_id) ON DELETE RESTRICT;
    END IF;
END $$;

ALTER TABLE ambulance.dispatch_assignments
    ADD COLUMN IF NOT EXISTS assigned_by UUID,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP;

ALTER TABLE ambulance.ambulance_trip_records
    ADD COLUMN IF NOT EXISTS dispatch_assignment_id UUID
        REFERENCES ambulance.dispatch_assignments(dispatch_assignment_id),
    ADD COLUMN IF NOT EXISTS recorded_by UUID;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_dispatch_request
    ON ambulance.dispatch_assignments(emergency_dispatch_request_id)
    WHERE assignment_status NOT IN ('Completed', 'Cancelled');

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_ambulance_assignment
    ON ambulance.dispatch_assignments(ambulance_id)
    WHERE assignment_status NOT IN ('Completed', 'Cancelled');

CREATE INDEX IF NOT EXISTS idx_dispatch_request_status_time
    ON ambulance.emergency_dispatch_requests(dispatch_status, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_dispatch_tracking_assignment_time
    ON ambulance.dispatch_tracking(dispatch_assignment_id, tracked_at DESC);
CREATE INDEX IF NOT EXISTS idx_gps_ambulance_time
    ON ambulance.gps_tracking_logs(ambulance_id, recorded_at DESC);

INSERT INTO ambulance.ambulance_types(type_code,type_name,emergency_level,description)
VALUES ('ALS','Advanced Life Support','Critical','Advanced cardiac and trauma response'),
       ('BLS','Basic Life Support','Urgent','Basic emergency and patient transport')
ON CONFLICT(type_code) DO NOTHING;

INSERT INTO ambulance.ambulances
    (ambulance_type_id,vehicle_number,registration_number,manufacturer_name,model_name,manufacturing_year,current_status,gps_enabled)
SELECT t.ambulance_type_id,v.vehicle_number,v.registration_number,'HMS Fleet',v.model_name,2025,'Available',TRUE
FROM ambulance.ambulance_types t
JOIN (VALUES ('ALS','AMB-ALS-01','HMS-ALS-01','Advanced Response'),
             ('BLS','AMB-BLS-01','HMS-BLS-01','Patient Transport'))
     AS v(type_code,vehicle_number,registration_number,model_name) ON v.type_code=t.type_code
ON CONFLICT(vehicle_number) DO NOTHING;

INSERT INTO ambulance.dispatch_priorities(priority_code,priority_name,response_time_target_minutes)
SELECT v.code,v.name,v.minutes FROM (VALUES
    ('P1','Immediate',8),('P2','Urgent',15),('P3','Routine',30)
) v(code,name,minutes)
WHERE NOT EXISTS (SELECT 1 FROM ambulance.dispatch_priorities p WHERE p.priority_code=v.code);

COMMIT;

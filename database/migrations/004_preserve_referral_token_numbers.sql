-- Preserve the original patient-facing OPD token across doctor referrals.
-- Repairs referral rows created by the former R-xxxxx implementation.

UPDATE queue_management.queue_tokens AS referral_token
SET token_number = source_token.token_number
FROM appointment.appointments AS referral_appointment,
     electronic_medical_records.patient_encounters AS source_encounter,
     queue_management.queue_tokens AS source_token
WHERE referral_token.appointment_id = referral_appointment.appointment_id
  AND referral_token.token_type = 'referral'
  AND referral_appointment.booking_source = 'Doctor Referral'
  AND referral_appointment.notes = 'Referred from encounter ' || source_encounter.encounter_number
  AND source_token.appointment_id = source_encounter.appointment_id
  AND referral_token.token_number LIKE 'R-%';

UPDATE electronic_medical_records.patient_encounters AS source_encounter
SET encounter_status = 'Completed', updated_at = CURRENT_TIMESTAMP
WHERE EXISTS (
    SELECT 1
    FROM appointment.appointments AS referral_appointment
    JOIN queue_management.queue_tokens AS referral_token
      ON referral_token.appointment_id = referral_appointment.appointment_id
    WHERE referral_appointment.booking_source = 'Doctor Referral'
      AND referral_appointment.notes = 'Referred from encounter ' || source_encounter.encounter_number
      AND referral_token.token_type = 'referral'
);

UPDATE appointment.appointments AS source_appointment
SET appointment_status_id = completed.appointment_status_id,
    completed_at = COALESCE(source_appointment.completed_at, CURRENT_TIMESTAMP),
    updated_at = CURRENT_TIMESTAMP
FROM appointment.appointment_statuses AS completed,
     electronic_medical_records.patient_encounters AS source_encounter
WHERE completed.status_name = 'Completed'
  AND source_encounter.appointment_id = source_appointment.appointment_id
  AND EXISTS (
      SELECT 1
      FROM appointment.appointments AS referral_appointment
      JOIN queue_management.queue_tokens AS referral_token
        ON referral_token.appointment_id = referral_appointment.appointment_id
      WHERE referral_appointment.booking_source = 'Doctor Referral'
        AND referral_appointment.notes = 'Referred from encounter ' || source_encounter.encounter_number
        AND referral_token.token_type = 'referral'
  );

UPDATE queue_management.queue_tokens AS source_token
SET status = 'completed', completed_at = COALESCE(source_token.completed_at, CURRENT_TIMESTAMP)
FROM electronic_medical_records.patient_encounters AS source_encounter
WHERE source_token.appointment_id = source_encounter.appointment_id
  AND EXISTS (
      SELECT 1
      FROM appointment.appointments AS referral_appointment
      JOIN queue_management.queue_tokens AS referral_token
        ON referral_token.appointment_id = referral_appointment.appointment_id
      WHERE referral_appointment.booking_source = 'Doctor Referral'
        AND referral_appointment.notes = 'Referred from encounter ' || source_encounter.encounter_number
        AND referral_token.token_type = 'referral'
  );

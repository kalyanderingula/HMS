# Diagnostic workflow: laboratory and radiology

This document defines what the HMS does after a patient attends the laboratory or imaging department and then leaves the hospital. It is the operational source of truth for reception, technicians, specialists, referring doctors, and patient-facing release rules.

## Responsibility matrix

| Activity | Responsible role | May approve/finalize? |
|---|---|---|
| Book a test or scan | Receptionist, patient, or doctor | No |
| Collect and label a specimen | Laboratory technician | No |
| Perform test and enter results | Laboratory technician | No |
| Review and release a laboratory report | Pathologist / laboratory-medicine doctor | Yes, laboratory only |
| Schedule and perform an imaging study | Radiology staff/technician | No |
| Interpret images and sign a report | Radiologist | Yes, radiology only |
| Review released results and decide treatment | Referring/treating doctor | No diagnostic sign-off |
| Arrange follow-up | Receptionist or treating doctor | No |

Administrators maintain users and configuration. Administrative access must not be treated as clinical authorization to sign a report.

## Laboratory lifecycle

```text
Ordered -> Sample Collected -> In Analysis -> Awaiting Pathologist Approval
        -> Approved/Released -> Completed
```

1. The order retains the patient, encounter/referral, ordering doctor, requested tests, priority, appointment time, and billing source.
2. At attendance, the technician confirms patient identity, records the specimen type and collection time, and assigns a barcode.
3. The technician performs the test and enters results only for parameters belonging to the ordered test.
4. The HMS selects the active reference-range version using the result date, patient age, sex, and applicable pregnancy/clinical context. It validates the result type and derives the result flag; a browser-supplied flag is not authoritative.
5. The entered result remains unreleased while awaiting a pathologist. The patient must not see it as a final report.
6. The pathologist reviews the result, quality information, flags, clinical notes, and previous results. Approval records the approver and timestamp and releases the report.
7. The laboratory order is complete only when every order item is complete.

Recommended result notifications:

| Result | Notification behavior |
|---|---|
| Normal | Notify that the approved report is available |
| High/Low | Notify that an abnormal approved report is available |
| Critical | Immediately alert the responsible clinical team and require acknowledgement |

## Radiology lifecycle

```text
Ordered -> Scheduled -> Study Performed -> Awaiting Radiologist
        -> Signed/Released -> Completed
```

1. Reception or the radiology desk schedules the ordered scan, modality, room, and appointment.
2. Imaging staff verify the patient and order, perform the study, and attach images/key images to the study or PACS reference.
3. The study enters the radiologist's reporting worklist after acquisition is complete.
4. The radiologist reviews images and records findings, impression, structured observations, and any critical finding.
5. Structured observations must belong to the scan that was ordered. Their types and configured allowed values must be validated by the server.
6. Only the authenticated radiologist signs the report. The HMS records the radiologist identity and approval timestamp.
7. The signed report is released to the referring doctor and patient, and the order becomes complete.
8. A critical finding immediately alerts the responsible clinician and remains open until acknowledged.

## Portal behavior after the patient leaves

- **Laboratory portal:** shows collected samples, tests in analysis, and reports awaiting pathology approval.
- **Radiology portal:** shows performed studies awaiting radiologist reporting and critical findings awaiting communication.
- **Doctor portal:** shows pending diagnostics as pending; only approved laboratory reports and signed radiology reports are clinical final results.
- **Patient portal:** exposes only approved/released reports. Draft results and internal quality notes are hidden.
- **Reception portal:** can view operational status and arrange follow-up, but cannot edit results or approve reports.

## Audit and data-retention requirements

For every release, retain the order and item identifiers, patient and encounter, specimen/study identifiers, entered values, reference-range version, entering user, approving user and specialty, entry/approval timestamps, report version, critical-alert delivery, and acknowledgement. Corrections should create a new version or amendment; released clinical data should not be silently overwritten.

## Current implementation status and known gaps

Migration `007_diagnostic_master_enhancement.sql` adds typed laboratory parameters, versioned reference ranges, imaging observations, and approval records. Migration `008_diagnostic_approval_roles.sql` adds the pathologist role and radiologist-user linkage.

The role restrictions and ordered-test ownership checks are implemented. Before production use, resolve the open diagnostic review findings tracked in `docs/IMPLEMENTATION_STATUS.md`, including laboratory create-schema and booking-response defects, qualitative interpretation, critical-notification classification, full reference-context matching, and server-side radiology value validation.

The bundled reference ranges are demonstration data. A qualified local laboratory must validate intervals, units, methods, analyzers, and critical thresholds before clinical use.

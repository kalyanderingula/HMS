"""Illustrative master reference intervals for development/demo use only.

Production intervals must be validated and versioned by the performing lab for
its population, method, analyser and units before results are released.
"""


def ref(test_code, parameter, rule, sex=None, age_min=None, age_max=None,
        low=None, high=None, unit=None, text=None, critical_low=None,
        critical_high=None, pregnancy_status=None, trimester=None):
    return locals()


REFERENCE_RANGES = [
    ref("LAB-CBC-01", "Hemoglobin", "SEX_AND_AGE_SPECIFIC", "MALE", 18, 120, 13.2, 16.6, "g/dL", critical_low=7, critical_high=20),
    ref("LAB-CBC-01", "Hemoglobin", "SEX_AND_AGE_SPECIFIC", "FEMALE", 18, 120, 11.6, 15.0, "g/dL", critical_low=7, critical_high=20),
    ref("LAB-CBC-01", "RBC Count", "SEX_AND_AGE_SPECIFIC", "MALE", 18, 120, 4.35, 5.65, "x10^12/L"),
    ref("LAB-CBC-01", "RBC Count", "SEX_AND_AGE_SPECIFIC", "FEMALE", 18, 120, 3.92, 5.13, "x10^12/L"),
    ref("LAB-CBC-01", "Hematocrit", "SEX_AND_AGE_SPECIFIC", "MALE", 18, 120, 40, 55, "%", critical_low=20, critical_high=60),
    ref("LAB-CBC-01", "Hematocrit", "SEX_AND_AGE_SPECIFIC", "FEMALE", 18, 120, 36, 48, "%", critical_low=20, critical_high=60),
    ref("LAB-CBC-01", "MCV", "ALL", low=80, high=100, unit="fL"),
    ref("LAB-CBC-01", "MCH", "ALL", low=27, high=32, unit="pg"),
    ref("LAB-CBC-01", "MCHC", "ALL", low=32, high=36, unit="g/dL"),
    ref("LAB-CBC-01", "WBC Count", "ALL", low=4, high=10, unit="x10^9/L", critical_low=2, critical_high=30),
    ref("LAB-CBC-01", "Platelet Count", "ALL", low=150, high=400, unit="x10^9/L", critical_low=20, critical_high=1000),
    ref("LAB-CBC-01", "Neutrophils", "ALL", low=40, high=70, unit="%"),
    ref("LAB-CBC-01", "Lymphocytes", "ALL", low=20, high=40, unit="%"),
    ref("LAB-CBC-01", "Monocytes", "ALL", low=2, high=10, unit="%"),
    ref("LAB-CBC-01", "Eosinophils", "ALL", low=1, high=6, unit="%"),
    ref("LAB-CBC-01", "Basophils", "ALL", low=0, high=2, unit="%"),
    ref("LAB-KFT-04", "Blood Urea Nitrogen", "ALL", low=7, high=20, unit="mg/dL"),
    ref("LAB-KFT-04", "Creatinine", "SEX_AND_AGE_SPECIFIC", "MALE", 18, 120, 0.7, 1.3, "mg/dL", critical_low=0.3, critical_high=10),
    ref("LAB-KFT-04", "Creatinine", "SEX_AND_AGE_SPECIFIC", "FEMALE", 18, 120, 0.6, 1.1, "mg/dL", critical_low=0.3, critical_high=10),
    ref("LAB-KFT-04", "eGFR", "AGE_SPECIFIC", age_min=18, age_max=120, low=60, unit="mL/min/1.73m2", text="Interpret using the configured eGFR equation and clinical context."),
    ref("LAB-ELEC-05", "Sodium", "ALL", low=135, high=145, unit="mmol/L", critical_low=120, critical_high=160),
    ref("LAB-ELEC-05", "Potassium", "ALL", low=3.5, high=5.0, unit="mmol/L", critical_low=2.5, critical_high=6.5),
    ref("LAB-ELEC-05", "Chloride", "ALL", low=98, high=106, unit="mmol/L", critical_low=80, critical_high=120),
    ref("LAB-ELEC-05", "Bicarbonate", "ALL", low=22, high=29, unit="mmol/L", critical_low=10, critical_high=40),
    ref("LAB-LFT-03", "Total Bilirubin", "ALL", low=0.1, high=1.2, unit="mg/dL"),
    ref("LAB-LFT-03", "Direct Bilirubin", "ALL", low=0, high=0.3, unit="mg/dL"),
    ref("LAB-LFT-03", "Total Protein", "ALL", low=6.0, high=8.3, unit="g/dL"),
    ref("LAB-LFT-03", "Albumin", "ALL", low=3.5, high=5.0, unit="g/dL"),
    ref("LAB-LFT-03", "Globulin", "ALL", low=2.0, high=3.5, unit="g/dL"),
    ref("LAB-LFT-03", "A/G Ratio", "ALL", low=1.0, high=2.5, unit="ratio"),
]


INTERPRETATION_RULES = [
    {"test_code":"LAB-DIAB-08", "parameter":"HbA1c", "code":"NORMAL", "label":"Normal", "operator":"LT", "upper":5.7, "priority":10},
    {"test_code":"LAB-DIAB-08", "parameter":"HbA1c", "code":"PREDIABETES", "label":"Prediabetes", "operator":"BETWEEN", "lower":5.7, "upper":6.4, "priority":20},
    {"test_code":"LAB-DIAB-08", "parameter":"HbA1c", "code":"DIABETES", "label":"Diabetes range", "operator":"GTE", "lower":6.5, "priority":30},
    {"test_code":"LAB-LIPID-06", "parameter":"Total Cholesterol", "code":"DESIRABLE", "label":"Desirable", "operator":"LT", "upper":200, "priority":10},
    {"test_code":"LAB-LIPID-06", "parameter":"Total Cholesterol", "code":"BORDERLINE", "label":"Borderline high", "operator":"BETWEEN", "lower":200, "upper":239, "priority":20},
    {"test_code":"LAB-LIPID-06", "parameter":"Total Cholesterol", "code":"HIGH", "label":"High", "operator":"GTE", "lower":240, "priority":30},
]

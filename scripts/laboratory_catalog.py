"""Configurable adult baseline laboratory catalog for demo and development.

Reference intervals are illustrative defaults. A production laboratory must
validate them for its analyser, method, specimen, units, age, sex, pregnancy
status, altitude, and local population before clinical use.
"""


def p(name, unit, interval, critical_low=None, critical_high=None):
    return {
        "name": name, "unit": unit, "range": interval,
        "critical_low": critical_low, "critical_high": critical_high,
    }


LAB_TEST_CATALOG = [
    {"code":"LAB-CBC-01","name":"Complete Blood Count with Differential","method":"5-part Hematology Analyzer","price":350,"tat":2,"volume":"2 mL EDTA whole blood","fasting":False,"parameters":[
        p("Hemoglobin","g/dL","Male 13.5-17.5; Female 12.0-15.5",7,20), p("Hematocrit","%","Male 41-53; Female 36-46",20,60),
        p("RBC Count","x10^6/uL","Male 4.5-5.9; Female 4.1-5.1"), p("MCV","fL","80-100"), p("MCH","pg","27-33"), p("MCHC","g/dL","32-36"), p("RDW-CV","%","11.5-14.5"),
        p("WBC Count","x10^3/uL","4.0-11.0",2,30), p("Neutrophils","%","40-70"), p("Lymphocytes","%","20-40"), p("Monocytes","%","2-8"), p("Eosinophils","%","1-4"), p("Basophils","%","0-1"),
        p("Absolute Neutrophil Count","x10^3/uL","1.5-7.5",0.5,20), p("Platelet Count","x10^3/uL","150-450",20,1000), p("MPV","fL","7.5-11.5") ]},
    {"code":"LAB-CMP-02","name":"Comprehensive Metabolic Panel","method":"Automated Chemistry Analyzer","price":900,"tat":4,"volume":"3 mL serum","fasting":True,"parameters":[
        p("Glucose","mg/dL","Fasting 70-99",40,500), p("Urea","mg/dL","15-40"), p("Blood Urea Nitrogen","mg/dL","7-20"), p("Creatinine","mg/dL","Male 0.7-1.3; Female 0.6-1.1",0.3,10), p("eGFR","mL/min/1.73m2",">=90"),
        p("Sodium","mmol/L","136-145",120,160), p("Potassium","mmol/L","3.5-5.1",2.5,6.5), p("Chloride","mmol/L","98-107",80,120), p("Bicarbonate","mmol/L","22-29",10,40), p("Calcium","mg/dL","8.6-10.2",6,13),
        p("Total Protein","g/dL","6.0-8.3"), p("Albumin","g/dL","3.5-5.0"), p("Total Bilirubin","mg/dL","0.3-1.2"), p("ALP","U/L","44-147"), p("ALT (SGPT)","U/L","7-56"), p("AST (SGOT)","U/L","10-40") ]},
    {"code":"LAB-LFT-03","name":"Liver Function Panel","method":"Photometric Assay","price":650,"tat":4,"volume":"3 mL serum","fasting":False,"parameters":[
        p("Total Bilirubin","mg/dL","0.3-1.2"), p("Direct Bilirubin","mg/dL","0.0-0.3"), p("Indirect Bilirubin","mg/dL","0.2-0.9"), p("ALT (SGPT)","U/L","7-56"), p("AST (SGOT)","U/L","10-40"), p("Alkaline Phosphatase","U/L","44-147"), p("GGT","U/L","Male 8-61; Female 5-36"), p("Total Protein","g/dL","6.0-8.3"), p("Albumin","g/dL","3.5-5.0"), p("Globulin","g/dL","2.0-3.5"), p("A/G Ratio","ratio","1.0-2.5") ]},
    {"code":"LAB-KFT-04","name":"Kidney Function Panel","method":"Automated Chemistry Analyzer","price":650,"tat":4,"volume":"3 mL serum","fasting":False,"parameters":[
        p("Urea","mg/dL","15-40"), p("Blood Urea Nitrogen","mg/dL","7-20"), p("Creatinine","mg/dL","Male 0.7-1.3; Female 0.6-1.1",0.3,10), p("eGFR","mL/min/1.73m2",">=90"), p("Uric Acid","mg/dL","Male 3.4-7.0; Female 2.4-6.0"), p("Calcium","mg/dL","8.6-10.2",6,13), p("Phosphorus","mg/dL","2.5-4.5") ]},
    {"code":"LAB-ELEC-05","name":"Serum Electrolytes","method":"Ion Selective Electrode","price":500,"tat":2,"volume":"2 mL serum/plasma","fasting":False,"parameters":[
        p("Sodium","mmol/L","136-145",120,160), p("Potassium","mmol/L","3.5-5.1",2.5,6.5), p("Chloride","mmol/L","98-107",80,120), p("Bicarbonate","mmol/L","22-29",10,40) ]},
    {"code":"LAB-LIPID-06","name":"Lipid Profile","method":"Enzymatic Colorimetry","price":550,"tat":4,"volume":"3 mL serum","fasting":True,"parameters":[
        p("Total Cholesterol","mg/dL","Desirable <200"), p("Triglycerides","mg/dL","Normal <150",None,500), p("HDL Cholesterol","mg/dL","Male >=40; Female >=50"), p("LDL Cholesterol","mg/dL","Optimal <100"), p("VLDL Cholesterol","mg/dL","5-40"), p("Non-HDL Cholesterol","mg/dL","Desirable <130"), p("Total Cholesterol/HDL Ratio","ratio","Target <5.0") ]},
    {"code":"LAB-THY-07","name":"Thyroid Profile (T3, T4, TSH)","method":"Chemiluminescent Immunoassay","price":850,"tat":6,"volume":"3 mL serum","fasting":False,"parameters":[
        p("TSH","uIU/mL","0.4-4.0"), p("Free T4","ng/dL","0.8-1.8"), p("Free T3","pg/mL","2.3-4.2") ]},
    {"code":"LAB-DIAB-08","name":"Diabetes Monitoring Panel","method":"Hexokinase and HPLC","price":650,"tat":4,"volume":"2 mL fluoride plasma + EDTA blood","fasting":True,"parameters":[
        p("Fasting Plasma Glucose","mg/dL","70-99",40,500), p("HbA1c","%","Normal <5.7; Prediabetes 5.7-6.4; Diabetes >=6.5"), p("Estimated Average Glucose","mg/dL","Calculated from HbA1c") ]},
    {"code":"LAB-COAG-09","name":"Coagulation Profile","method":"Optical Coagulometry","price":700,"tat":2,"volume":"2.7 mL citrate plasma","fasting":False,"parameters":[
        p("Prothrombin Time (PT)","seconds","11-13.5",None,30), p("INR","ratio","0.8-1.2; therapeutic target depends on indication",None,5), p("aPTT","seconds","25-35",None,70), p("Fibrinogen","mg/dL","200-400",100,700), p("D-Dimer","ng/mL FEU","<500") ]},
    {"code":"LAB-IRON-10","name":"Iron Studies","method":"Colorimetry and Immunoassay","price":900,"tat":8,"volume":"3 mL serum","fasting":True,"parameters":[
        p("Serum Iron","ug/dL","Male 65-175; Female 50-170"), p("TIBC","ug/dL","250-450"), p("Transferrin Saturation","%","20-50"), p("Ferritin","ng/mL","Male 30-400; Female 15-150") ]},
    {"code":"LAB-CARD-11","name":"Cardiac Marker Panel","method":"High-sensitivity Immunoassay","price":1600,"tat":1,"volume":"3 mL serum/plasma","fasting":False,"parameters":[
        p("High-sensitivity Troponin I","ng/L","Assay/sex-specific 99th percentile",None,100), p("CK-MB","ng/mL","<5.0"), p("Total CK","U/L","Male 39-308; Female 26-192"), p("NT-proBNP","pg/mL","Age and clinical-context specific") ]},
    {"code":"LAB-INFL-12","name":"Inflammation Panel","method":"Immunoturbidimetry and Westergren","price":650,"tat":4,"volume":"Serum + EDTA whole blood","fasting":False,"parameters":[
        p("C-Reactive Protein","mg/L","<5"), p("ESR","mm/hr","Male 0-15; Female 0-20"), p("Procalcitonin","ng/mL","<0.1") ]},
    {"code":"LAB-VIT-13","name":"Vitamin B12 and Folate","method":"Chemiluminescent Immunoassay","price":1200,"tat":12,"volume":"3 mL serum","fasting":True,"parameters":[
        p("Vitamin B12","pg/mL","200-900"), p("Serum Folate","ng/mL",">4.0") ]},
    {"code":"LAB-VITD-14","name":"25-Hydroxy Vitamin D","method":"Chemiluminescent Immunoassay","price":1100,"tat":12,"volume":"3 mL serum","fasting":False,"parameters":[p("25-OH Vitamin D","ng/mL","Deficient <20; insufficient 20-29; sufficient 30-100",None,150)]},
    {"code":"LAB-PANC-15","name":"Pancreatic Enzymes","method":"Enzymatic Colorimetry","price":800,"tat":4,"volume":"3 mL serum","fasting":False,"parameters":[p("Amylase","U/L","30-110"),p("Lipase","U/L","13-60")]},
    {"code":"LAB-MIN-16","name":"Bone and Mineral Panel","method":"Photometric Assay","price":750,"tat":4,"volume":"3 mL serum","fasting":False,"parameters":[p("Calcium","mg/dL","8.6-10.2",6,13),p("Phosphorus","mg/dL","2.5-4.5"),p("Magnesium","mg/dL","1.7-2.4",1,4.8),p("Alkaline Phosphatase","U/L","44-147")]},
    {"code":"LAB-ABG-17","name":"Arterial Blood Gas with Lactate","method":"Blood Gas Analyzer","price":900,"tat":1,"volume":"1 mL heparinized arterial blood","fasting":False,"parameters":[p("pH","","7.35-7.45",7.2,7.6),p("pCO2","mmHg","35-45",20,70),p("pO2","mmHg","80-100",40,None),p("Bicarbonate","mmol/L","22-26",10,40),p("Oxygen Saturation","%","95-100",75,None),p("Lactate","mmol/L","0.5-2.2",None,4)]},
    {"code":"LAB-SEPSIS-18","name":"Sepsis Screening Panel","method":"Automated Chemistry and Immunoassay","price":1450,"tat":2,"volume":"Serum/plasma + EDTA blood","fasting":False,"parameters":[p("Procalcitonin","ng/mL","<0.1"),p("C-Reactive Protein","mg/L","<5"),p("Lactate","mmol/L","0.5-2.2",None,4),p("WBC Count","x10^3/uL","4.0-11.0",2,30)]},
    {"code":"LAB-HEP-19","name":"Viral Hepatitis Screening","method":"CLIA","price":1400,"tat":12,"volume":"4 mL serum","fasting":False,"parameters":[p("HBsAg","index","Non-reactive"),p("Anti-HCV","index","Non-reactive"),p("Anti-HAV IgM","index","Non-reactive"),p("Anti-HEV IgM","index","Non-reactive")]},
    {"code":"LAB-HIV-20","name":"HIV-1/2 Antigen and Antibody Screen","method":"4th Generation CLIA","price":700,"tat":12,"volume":"3 mL serum/plasma","fasting":False,"parameters":[p("HIV-1/2 Ag/Ab","index","Non-reactive; reactive screens require confirmatory testing")]},
    {"code":"LAB-BG-21","name":"ABO and Rh Blood Group","method":"Column Agglutination","price":300,"tat":2,"volume":"2 mL EDTA whole blood","fasting":False,"parameters":[p("ABO Group","","A, B, AB, or O"),p("Rh(D)","","Positive or Negative")]},
]

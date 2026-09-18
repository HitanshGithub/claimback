"""Generate fictional claim scenario packs for ClaimBack under samples/.

Each scenario folder gets:
  policy_schedule.pdf, hospital_bill.pdf, discharge_summary.pdf, insurer_letter.pdf  (rendered via headless Chrome)
  line_items.json   ground truth of what OCR / extraction should read from the bill
  expected.json     ground truth verdict per deduction, with citations into data/*.json
Scenario 1 also gets hospital_bill_photo.jpg (skewed, shadowed "phone photo") for OCR robustness tests.

All people, hospitals and insurers are fictional. Amounts are chosen so every total is a whole rupee.

Usage: python scripts/build_samples.py
"""

import json
import random
import subprocess
import tempfile
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"
CHROME = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
NON_PAYABLE = json.loads((ROOT / "data/non_payable_items.json").read_text(encoding="utf-8"))

COPAY_PCT = 5
FOOTER = "FICTIONAL SAMPLE DOCUMENT - created for the ClaimBack demo. Not issued by any real hospital or insurer."

INSURER = {
    "name": "Nirmaan Health Insurance Co. Ltd.",
    "address": "Claims Department, 4th Floor, Unity Towers, MG Road, Bengaluru - 560001",
    "tollfree": "1800-000-4455",
    "gro_email": "gro@nirmaanhealth.example",
    "web": "www.nirmaanhealth.example",
}

HOSPITALS = {
    "lakeview": {"name": "Lakeview Multispeciality Hospital", "address": "27th Main, Sector 2, HSR Layout, Bengaluru - 560102", "gstin": "Healthcare services exempt from GST", "network": True},
    "greenfield": {"name": "Greenfield Hospital", "address": "100 Feet Road, Indiranagar, Bengaluru - 560038", "gstin": "Healthcare services exempt from GST", "network": False},
    "riverbend": {"name": "Riverbend Heart Institute", "address": "9th Block, Jayanagar, Bengaluru - 560069", "gstin": "Healthcare services exempt from GST", "network": False},
    "northstar": {"name": "Northstar Ortho & Sports Injury Hospital", "address": "80 Feet Road, Koramangala 4th Block, Bengaluru - 560034", "gstin": "Healthcare services exempt from GST", "network": True},
}


def np_id(item_name: str) -> str:
    """Look up the Arogya Sanjeevani non-payable list id for an exact item name."""
    for it in NON_PAYABLE["items"]:
        if it["schedule"] == "arogya_sanjeevani" and it["item"].upper() == item_name.upper():
            return it["id"]
    raise KeyError(item_name)


def inr(amount: float) -> str:
    """Indian digit grouping: 139700 -> 1,39,700.00"""
    rupees = int(round(amount * 100)) // 100
    paise = int(round(amount * 100)) % 100
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{s}.{paise:02d}"


@dataclass
class Line:
    code: str
    head: str  # room | icu | nursing | doctor | ot | pharmacy | investigations | implant | consumable | misc | ambulance
    description: str
    qty: int
    rate: int

    @property
    def amount(self) -> int:
        return self.qty * self.rate


@dataclass
class Deduction:
    code: str | None  # bill line code, or None for computed deductions (proportionate, etc.)
    amount: int
    insurer_reason: str
    verdict: str  # fair | challengeable | fair_ask_hospital_to_absorb | needs_more_info
    explanation: str
    citations: list[str] = field(default_factory=list)
    strength: str | None = None  # strong | moderate | weak (for challengeable / needs_more_info)
    description: str | None = None


@dataclass
class Scenario:
    sid: str
    slug: str
    title: str
    summary: str
    wording_id: str
    patient: dict
    policy: dict
    admission: dict
    lines: list[Line]
    deductions: list[Deduction]
    letter: dict
    discharge: dict
    extra_expected: dict = field(default_factory=dict)
    photo: bool = False

    @property
    def hospital(self) -> dict:
        return HOSPITALS[self.admission["hospital"]]

    def line(self, code: str) -> Line:
        return next(l for l in self.lines if l.code == code)

    def totals(self) -> dict:
        claimed = sum(l.amount for l in self.lines)
        deducted = sum(d.amount for d in self.deductions)
        if self.letter["type"] == "repudiation":
            return {"claimed": claimed, "deducted": claimed, "admissible": 0, "co_payment": 0, "paid": 0}
        admissible = claimed - deducted
        copay = admissible * COPAY_PCT / 100
        assert copay == int(copay), f"{self.sid}: co-pay {copay} not whole rupees"
        return {"claimed": claimed, "deducted": deducted, "admissible": admissible, "co_payment": int(copay), "paid": admissible - int(copay)}


# --------------------------------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------------------------------

def scenario_1() -> Scenario:
    lines = [
        Line("RM01", "room", "Room Rent - Single Room AC (incl. nursing & boarding)", 3, 4500),
        Line("NR01", "nursing", "Nursing Care Charges", 3, 800),
        Line("DR01", "doctor", "Consultant Visit - Dr. K. Rao (General Surgery)", 3, 1500),
        Line("DR02", "doctor", "Surgeon Fee - Laparoscopic Cholecystectomy", 1, 45000),
        Line("DR03", "doctor", "Anaesthetist Fee", 1, 12000),
        Line("OT01", "ot", "Operation Theatre Charges (Major)", 1, 18000),
        Line("PH01", "pharmacy", "Pharmacy - Medicines, Antibiotics & IV Fluids (as per annexure)", 1, 14860),
        Line("IN01", "investigations", "Investigations - CBC, LFT, RFT, Coagulation, USG Abdomen, ECG, Chest X-Ray", 1, 9600),
        Line("IN02", "investigations", "Histopathology - Gallbladder Specimen", 1, 2350),
        Line("CS01", "consumable", "Sutures - Vicryl 2-0 / Prolene 3-0", 6, 600),
        Line("CS02", "consumable", "Hem-o-lok Ligation Clips (Medium-Large)", 6, 700),
        Line("CS03", "consumable", "Closed Suction Drain Set (Romovac 14Fr)", 1, 1450),
        Line("CS04", "consumable", "Examination Gloves (pairs)", 31, 40),
        Line("CS05", "consumable", "IV Cannula - Vasofix Safety 20G", 1, 350),
        Line("CS06", "consumable", "Nebulizer Kit", 1, 650),
        Line("CS07", "consumable", "Gauze & Cotton (sterile)", 1, 900),
        Line("MS01", "misc", "Admission Kit", 1, 1200),
        Line("MS02", "misc", "Registration Charges", 1, 500),
        Line("MS03", "misc", "Attendant Food Charges", 1, 2100),
        Line("MS04", "misc", "Pulse Oximeter Charges", 3, 200),
        Line("MS05", "misc", "Documentation Charges", 1, 400),
        Line("MS06", "misc", "Medical Records Copy Charges", 1, 300),
    ]
    hosp_bill = "It was a cashless claim at a network hospital, so you can ask the hospital to absorb it - but since the 2020 IRDAI circular was superseded in 2024 this is a request, not an enforceable right."
    deductions = [
        Deduction("CS01", 3600, "Non-payable consumables", "challengeable",
                  "Sutures are not in the policy's Annexure-A List I-IV and are a medically necessary part of surgery, covered under Section 4.1(iv) (surgical appliances and similar expenses). No deduction can be made for an exclusion not written in the policy, and the letter cites no clause.",
                  ["NIVA-AS-4.7-LISTS", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS", "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"], "strong"),
        Deduction("CS02", 4200, "Non-payable consumables", "challengeable",
                  "Ligation clips stay inside the body to close the cystic duct/artery - they work like an implant/surgical appliance and are not in the policy's Annexure-A lists or any written exclusion.",
                  ["NIVA-AS-4.7-LISTS", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS", "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"], "strong"),
        Deduction("CS03", 1450, "Non-payable consumables", "challengeable",
                  "A surgical drain is a medically necessary surgical consumable that is not in the policy's Annexure-A lists or any written exclusion.",
                  ["NIVA-AS-4.7-LISTS", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"], "moderate"),
        Deduction("IN02", 2350, "Diagnostic expenses not related to current treatment (Code Excl04)", "challengeable",
                  "Excl04 only excludes diagnostics 'not related or not incidental to the current diagnosis and treatment'. Histopathology of the gallbladder removed in this very surgery is incidental to the treatment.",
                  ["NIVA-AS-7.1-EVAL", "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"], "strong"),
        Deduction("CS04", 1240, "Non-payable item - List I", "fair", "Gloves are List I (not covered) in Arogya Sanjeevani.", [np_id("GLOVES")]),
        Deduction("CS05", 350, "Non-payable item - List I", "fair", "Vasofix Safety is List I (not covered).", [np_id("VASOFIX SAFETY")]),
        Deduction("CS06", 650, "Non-payable item - List I", "fair", "Nebulizer kit is List I (not covered).", [np_id("NEBULIZER KIT")]),
        Deduction("CS07", 900, "Subsumed into procedure charges - List III", "fair_ask_hospital_to_absorb",
                  "Gauze and cotton are List III - part of the procedure charge, so not payable as a separate line. " + hosp_bill,
                  [np_id("GAUZE"), np_id("COTTON")]),
        Deduction("MS01", 1200, "Subsumed into room charges - List II", "fair_ask_hospital_to_absorb",
                  "Admission kit is List II - part of room charges. " + hosp_bill, [np_id("ADMISSION KIT")]),
        Deduction("MS02", 500, "Subsumed into cost of treatment - List IV", "fair_ask_hospital_to_absorb",
                  "Registration charges are List IV - part of treatment cost. " + hosp_bill, [np_id("ADMISSION/REGISTRATION CHARGES")]),
        Deduction("MS03", 2100, "Non-payable item - List I", "fair", "Food for attendants is List I (not covered).",
                  [np_id("FOOD CHARGES (OTHER THAN PATIENT's DIET PROVIDED BY HOSPITAL)")]),
        Deduction("MS04", 600, "Subsumed into room charges - List II", "fair_ask_hospital_to_absorb",
                  "Pulse oximeter charges are List II - part of room charges. " + hosp_bill, [np_id("PULSEOXYMETER CHARGES")]),
        Deduction("MS05", 400, "Subsumed into room charges - List II", "fair_ask_hospital_to_absorb",
                  "Documentation charges are List II - part of room charges. " + hosp_bill, [np_id("DOCUMENTATION CHARGES / ADMINISTRATIVE EXPENSES")]),
        Deduction("MS06", 300, "Non-payable item - List I", "fair", "Medical records charges are List I (not covered).", [np_id("MEDICAL RECORDS")]),
    ]
    return Scenario(
        sid="S1", slug="s1-consumables-mix-cashless",
        title="Gallbladder surgery - 'non-payable consumables' deductions (cashless)",
        summary="Cashless laparoscopic cholecystectomy at a network hospital. The insurer deducted 14 lines as non-payable; 4 of them (sutures, ligation clips, drain, histopathology) are not on any IRDAI list or were wrongly excluded.",
        wording_id="AS-NIVA-2026",
        patient={"name": "Sunita Sharma", "age": 52, "gender": "Female", "uhid": "LMH-2026-448812", "ip_no": "IP/26/08/1193", "relation": "Self"},
        policy={"policy_no": "NHI/AS/2026/0073311", "sum_insured": 500000, "cumulative_bonus": 75000, "period": ("10-01-2026", "09-01-2027"), "first_inception": "10-01-2023", "history": "Continuous with Nirmaan Health since 10-01-2023", "peds_declared": "None", "city": "Bengaluru", "phone": "98450 00000"},
        admission={"hospital": "lakeview", "claim_type": "Cashless", "doa": "03-08-2026", "dod": "06-08-2026", "doctor": "Dr. K. Rao, MS (General Surgery)", "ward": "Single Room AC", "diagnosis": "Symptomatic cholelithiasis (gallbladder stones) with chronic cholecystitis", "procedure": "Laparoscopic cholecystectomy", "icd": "K80.10"},
        lines=lines, deductions=deductions,
        letter={"type": "settlement", "date": "06-08-2026", "claim_no": "CLM-NHI-26-0845521", "received": "06-08-2026", "mode": "Cashless - final authorisation at discharge"},
        extra_expected={
            "other_checks": [
                {"issue": "Deduction letter does not cite policy clauses", "verdict": "challengeable", "strength": "moderate",
                 "explanation": "Three deductions say only 'Non-payable consumables'. A partial disallowance must give full details with reference to the specific terms and conditions of the policy - ask the insurer to name the clause for each.",
                 "citations": ["R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"]},
                {"issue": "Specific waiting period for gallbladder calculi", "verdict": "not_applicable",
                 "explanation": "Calculi of the gall bladder have a 24-month waiting period; the policy has been continuous since 10-01-2023 (43 months at admission).",
                 "citations": ["NIVA-AS-6.3-SPECIFIC"]},
            ],
        },
        discharge={"history": "52-year-old female with recurrent right upper quadrant pain after fatty meals for 5 months. USG abdomen: multiple calculi in gallbladder, wall thickening 4 mm. No jaundice.", "course": "Underwent elective laparoscopic cholecystectomy under GA on 04-08-2026. Intra-op: chronically inflamed gallbladder with multiple calculi; cystic duct and artery clipped with Hem-o-lok clips; drain placed. Specimen sent for histopathology. Post-op uneventful, drain removed on POD 2.", "advice": "Soft diet for 1 week. Tab. Paracetamol 650 mg SOS. Review in surgery OPD after 7 days with histopathology report.", "comorbidities": "No known comorbidities"},
        photo=True,
    )


def scenario_2() -> Scenario:
    lines = [
        Line("RM01", "room", "Room Rent - Deluxe Single Room (incl. nursing & boarding)", 5, 8000),
        Line("DR01", "doctor", "Consultant Visits - Dr. S. Pillai (Pulmonology)", 10, 1200),
        Line("PH01", "pharmacy", "Pharmacy - Antibiotics, Nebulisation Drugs & IV Fluids", 1, 38400),
        Line("IN01", "investigations", "Investigations - HRCT Chest, Blood Cultures, CBC, CRP, Procalcitonin, ABG", 1, 22400),
        Line("CS01", "consumable", "Examination Gloves (pairs)", 20, 40),
        Line("MS01", "misc", "Attendant Bed Charges", 5, 500),
    ]
    room_cap = 5000  # 2% of 3,00,000 = 6,000, capped at Rs 5,000/day
    ratio_cut = 1 - room_cap / 8000  # 0.375
    insurer_base = sum(l.amount for l in lines if l.head in ("room", "doctor", "pharmacy", "investigations"))
    correct_base = sum(l.amount for l in lines if l.head in ("room", "doctor"))  # associated medical expenses under Niva 4.1 Note 2
    star_base = sum(l.amount for l in lines if l.head in ("room", "doctor", "investigations"))  # Star: all except medicines
    insurer_prop = int(insurer_base * ratio_cut)
    correct_prop = int(correct_base * ratio_cut)
    star_prop = int(star_base * ratio_cut)
    deductions = [
        Deduction(None, correct_prop, "Proportionate deduction - room rent Rs 8,000/day exceeds eligible Rs 5,000/day (62.5% payable)", "fair",
                  f"Pro-rata on associated medical expenses (room incl. nursing Rs {inr(40000)} + doctor fees Rs {inr(12000)}) is allowed by Section 4.1 Note 2.",
                  ["NIVA-AS-4.1-ROOM", "NIVA-AS-4.1-PRORATA"], description="Proportionate deduction on room rent & doctor fees"),
        Deduction(None, insurer_prop - correct_prop, "Proportionate deduction - room rent Rs 8,000/day exceeds eligible Rs 5,000/day (62.5% payable)", "challengeable",
                  f"The insurer applied the 37.5% cut to pharmacy (Rs {inr(38400)}) and investigations (Rs {inr(22400)}) too. Under this policy's Section 4.1 Note 2, associated medical expenses are only room rent, nursing, medical practitioners' fees and OT charges - so medicines and diagnostics must be paid in full.",
                  ["NIVA-AS-4.1-PRORATA", "R-POLICY-MUST-STATE-SUBLIMITS-PROPORTIONATE-DEDUCTIONS", "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS"], "strong", description="Proportionate deduction wrongly applied to pharmacy & investigations"),
        Deduction("CS01", 800, "Non-payable item - List I", "fair", "Gloves are List I (not covered).", [np_id("GLOVES")]),
        Deduction("MS01", 2500, "Non-payable item - List I", "fair", "Attendant charges are List I (not covered).", [np_id("ATTENDANT CHARGES")]),
    ]
    challenge = insurer_prop - correct_prop
    return Scenario(
        sid="S2", slug="s2-proportionate-deduction",
        title="Pneumonia admission - proportionate deduction applied to the whole bill",
        summary="Patient stayed in a Rs 8,000/day room against a Rs 5,000/day limit. The insurer cut 37.5% from room, doctor fees, pharmacy AND investigations. Under the Niva Bupa wording only room/nursing/doctor/OT charges can be pro-rated.",
        wording_id="AS-NIVA-2026",
        patient={"name": "Rajesh Kumar", "age": 58, "gender": "Male", "uhid": "GFH-2026-102934", "ip_no": "IP-7781/26", "relation": "Self"},
        policy={"policy_no": "NHI/AS/2025/0419087", "sum_insured": 300000, "cumulative_bonus": 30000, "period": ("01-04-2026", "31-03-2027"), "first_inception": "01-04-2022", "history": "Continuous with Nirmaan Health since 01-04-2022", "peds_declared": "None", "city": "Bengaluru", "phone": "99000 00000"},
        admission={"hospital": "greenfield", "claim_type": "Reimbursement", "doa": "14-07-2026", "dod": "19-07-2026", "doctor": "Dr. S. Pillai, MD DM (Pulmonology)", "ward": "Deluxe Single Room", "diagnosis": "Community-acquired pneumonia, right lower lobe", "procedure": "Medical management (IV antibiotics, nebulisation, oxygen support)", "icd": "J18.1"},
        lines=lines, deductions=deductions,
        letter={"type": "settlement", "date": "04-08-2026", "claim_no": "CLM-NHI-26-0791240", "received": "24-07-2026", "mode": "Reimbursement - NEFT"},
        discharge={"history": "58-year-old male with fever, productive cough and breathlessness for 4 days. SpO2 91% on room air. HRCT chest: right lower lobe consolidation.", "course": "Admitted to deluxe room at patient's request. Treated with IV Piperacillin-Tazobactam, Azithromycin, nebulisation and intermittent oxygen. Fever settled by day 3; SpO2 97% on room air by day 4. Discharged in stable condition.", "advice": "Tab. Amoxicillin-Clavulanate 625 mg BD x 5 days. Repeat chest X-ray after 2 weeks.", "comorbidities": "No known comorbidities"},
        extra_expected={
            "room_rent_check": {"actual_per_day": 8000, "eligible_per_day": room_cap, "payable_ratio": room_cap / 8000,
                                "insurer_pro_rated_base": insurer_base, "correct_pro_rated_base": correct_base},
            "alternate_wordings": [{
                "wording_id": "AS-STAR-2025",
                "note": "Same bill under Star Health's Arogya Sanjeevani wording, which exempts only medicines from proportionate deduction.",
                "correct_proportionate_deduction": star_prop,
                "challengeable_amount": insurer_prop - star_prop,
                "estimated_additional_payable_after_copay": int((insurer_prop - star_prop) * (100 - COPAY_PCT) / 100),
                "citations": ["STAR-AS-PRORATA"],
            }],
            "demo_point": f"Same bill, two insurers' 'standard' wordings: Rs {inr(challenge)} challengeable under Niva Bupa vs Rs {inr(insurer_prop - star_prop)} under Star Health.",
        },
    )


def scenario_3() -> Scenario:
    lines = [
        Line("IC01", "icu", "ICCU Charges (incl. nursing & monitoring)", 2, 9000),
        Line("RM01", "room", "Room Rent - Single Room (incl. nursing)", 2, 4500),
        Line("DR01", "doctor", "Interventional Cardiologist Fee - PTCA", 1, 60000),
        Line("DR02", "doctor", "Consultant Visits - Cardiology", 4, 1500),
        Line("OT01", "ot", "Cath Lab Charges", 1, 45000),
        Line("IM01", "implant", "Drug Eluting Stent 3.0 x 28 mm (with sticker)", 1, 31500),
        Line("CS01", "consumable", "Cath Lab Disposables - Guide Catheter, Guide Wire, PTCA Balloon, Inflation Device", 1, 42000),
        Line("PH01", "pharmacy", "Pharmacy - Antiplatelets, Heparin, Statins, IV Fluids", 1, 28600),
        Line("IN01", "investigations", "Investigations - ECG, 2D Echo, Troponin-I, Lipid Profile, HbA1c, RFT", 1, 16400),
        Line("MS01", "misc", "Attendant Charges", 2, 500),
        Line("MS02", "misc", "Attendant Food Charges", 1, 1600),
    ]
    claimed = sum(l.amount for l in lines)
    admissible_if_accepted = claimed - 2600
    return Scenario(
        sid="S3", slug="s3-non-disclosure-after-moratorium",
        title="Heart attack - claim rejected for 'non-disclosure' after 7 years of cover",
        summary="Claim of Rs 2,59,100 fully repudiated because diabetes and hypertension were allegedly not disclosed at inception in 2019. The insured has 84+ months of continuous cover (ported in 2023), so the 60-month moratorium bars non-disclosure grounds unless fraud is established. The decision also came late.",
        wording_id="AS-NIVA-2026",
        patient={"name": "Meena Iyer", "age": 64, "gender": "Female", "uhid": "RHI-2026-033571", "ip_no": "IP/CARD/26/0712", "relation": "Self"},
        policy={"policy_no": "NHI/AS/2026/0102245", "sum_insured": 500000, "cumulative_bonus": 50000, "period": ("15-06-2026", "14-06-2027"), "first_inception": "15-06-2023", "history": "15-06-2019 to 14-06-2023: Vardaan General Insurance Co. Ltd. (Arogya Sanjeevani), continuously renewed. Ported to Nirmaan Health on 15-06-2023 with full continuity benefits.", "peds_declared": "None", "city": "Bengaluru", "phone": "94480 00000"},
        admission={"hospital": "riverbend", "claim_type": "Reimbursement (cashless request denied pending investigation)", "doa": "10-07-2026", "dod": "14-07-2026", "doctor": "Dr. A. Venkatesh, DM (Cardiology)", "ward": "ICCU / Single Room", "diagnosis": "Acute anterior wall ST-elevation myocardial infarction", "procedure": "Primary PTCA with drug eluting stent to LAD", "icd": "I21.0"},
        lines=lines,
        deductions=[],
        letter={"type": "repudiation", "date": "21-08-2026", "claim_no": "CLM-NHI-26-0733019", "received": "22-07-2026", "mode": "Reimbursement",
                "reason": "On scrutiny of the indoor case papers, it is observed that the insured patient is a known case of Type 2 Diabetes Mellitus and Hypertension for 10 years. These conditions were not disclosed in the proposal form at the time of inception of the policy. As the claim is related to the non-disclosed pre-existing conditions, the claim stands repudiated under Clause 10.1 (Disclosure of Information) and Code Excl01 (Pre-Existing Diseases) of the policy terms and conditions."},
        discharge={"history": "64-year-old female presented with retrosternal chest pain radiating to left arm for 2 hours with sweating. ECG: ST elevation V1-V4. Troponin-I elevated. Known case of Type 2 Diabetes Mellitus and Hypertension for 10 years on Tab. Metformin 500 mg BD and Tab. Telmisartan 40 mg OD.", "course": "Taken up for primary PTCA: 95% thrombotic occlusion of proximal LAD; DES 3.0 x 28 mm deployed with TIMI III flow. Monitored in ICCU for 48 hours, shifted to room. LVEF 45%. Uneventful recovery.", "advice": "Tab. Aspirin 75 mg OD, Tab. Ticagrelor 90 mg BD, Tab. Atorvastatin 80 mg HS, continue diabetes and BP medication. Cardiac rehab. Review after 2 weeks.", "comorbidities": "T2DM, HTN - 10 years"},
        extra_expected={
            "rejection_checks": [
                {"issue": "Non-disclosure / misrepresentation after moratorium", "verdict": "challengeable", "strength": "strong",
                 "explanation": "Continuous coverage from 15-06-2019 (including portability) to admission on 10-07-2026 is 84 months - beyond the 60-month moratorium. After that, no claim is contestable on grounds of non-disclosure or misrepresentation except established fraud, and the letter does not allege or prove fraud.",
                 "computed": {"continuous_cover_start": "2019-06-15", "admission_date": "2026-07-10", "continuous_months": 84, "moratorium_months": 60},
                 "citations": ["NIVA-AS-8-MORATORIUM", "R-MORATORIUM-60M", "R-PORTABILITY-CREDITS"]},
                {"issue": "Pre-existing disease exclusion (Excl01)", "verdict": "challengeable", "strength": "strong",
                 "explanation": "Even if diabetes/hypertension are treated as PEDs, the PED waiting period is 36 months of continuous coverage and portability credit counts; 84 months have elapsed. The insurer relies on the 'declared and accepted' condition, which is exactly the non-disclosure ground the moratorium bars.",
                 "citations": ["NIVA-AS-6.1-PED", "R-PED-WAITING-MAX-36M", "R-PORTABILITY-CREDITS", "NIVA-AS-8-MORATORIUM"]},
                {"issue": "Moratorium caveat - permanent exclusions", "verdict": "not_applicable",
                 "explanation": "The moratorium does not override permanent exclusions written in the policy. Heart disease is not a permanent exclusion in this wording, so the caveat does not save the rejection.",
                 "citations": ["R-MORATORIUM-PERMANENT-EXCLUSIONS-SURVIVE"]},
                {"issue": "What exactly the proposal form asked", "verdict": "needs_more_info", "strength": "moderate",
                 "explanation": "Non-disclosure can only relate to information explicitly sought in the proposal form. Ask the insurer for a copy of the 2019 proposal form and the portability records - useful if the moratorium argument is disputed.",
                 "citations": ["R-MATERIAL-INFORMATION-ONLY-WHAT-PROPOSAL-ASKED", "R-PROPOSAL-FORM-COPY-WITHIN-15-DAYS"]},
                {"issue": "Repudiation approval", "verdict": "needs_more_info", "strength": "moderate",
                 "explanation": "No claim may be repudiated without approval of the insurer's Product Management Committee / Claims Review Committee. Ask the insurer to confirm CRC approval.",
                 "citations": ["R-REPUDIATION-NEEDS-CRC-APPROVAL"]},
                {"issue": "Good-faith misstatement", "verdict": "challengeable", "strength": "moderate",
                 "explanation": "Fraud requires deliberate intent; a policyholder who did not think controlled diabetes/BP had to be declared can rely on the good-faith proviso.",
                 "citations": ["NIVA-AS-10.9-FRAUD"]},
                {"issue": "Delayed decision - penal interest", "verdict": "challengeable", "strength": "strong",
                 "explanation": "Documents received 22-07-2026; decision issued 21-08-2026 = 30 days, beyond the 15 days in Section 9.6. If the claim is later paid, interest at 2% above bank rate is due from the date of claim intimation.",
                 "computed": {"documents_received": "2026-07-22", "decision_date": "2026-08-21", "days_taken": 30, "allowed_days": 15},
                 "citations": ["NIVA-AS-9.6-SETTLEMENT", "R-REIMBURSEMENT-SETTLEMENT-15-DAYS", "R-CLAIM-DELAY-INTEREST", "R-BANK-RATE-DEFINITION"]},
            ],
            "next_steps": [
                {"step": 1, "action": "Written grievance to the insurer's GRO citing the moratorium, portability credits and delay interest; request the proposal form copy and CRC approval.", "deadline": "Insurer must resolve within 14 days", "citations": ["R-GRIEVANCE-ACK-IMMEDIATE-RESOLVE-14-DAYS"]},
                {"step": 2, "action": "Register the complaint on Bima Bharosa in parallel for tracking.", "citations": ["R-BIMA-BHAROSA-ONLINE-COMPLAINT"]},
                {"step": 3, "action": "If rejected, unanswered for 30 days or unsatisfactory: file with the Insurance Ombudsman, Bengaluru (free; within 1 year; claim up to Rs 50 lakh).", "citations": ["R-OMBUDSMAN-AFTER-30-DAYS-OR-UNSATISFACTORY-DECISION", "R-OMBUDSMAN-ONE-YEAR-LIMIT", "R-OMBUDSMAN-NO-FEE-FILING-MODES", "R-OMBUDSMAN-CLAIMS-UP-TO-50-LAKH"]},
            ],
            "if_claim_accepted": {"claimed": claimed, "non_payable_list_i": 2600, "admissible": admissible_if_accepted,
                                  "co_payment": int(admissible_if_accepted * COPAY_PCT / 100),
                                  "estimated_payable": admissible_if_accepted - int(admissible_if_accepted * COPAY_PCT / 100),
                                  "non_payable_citations": [np_id("ATTENDANT CHARGES"), np_id("FOOD CHARGES (OTHER THAN PATIENT's DIET PROVIDED BY HOSPITAL)")]},
        },
    )


def scenario_4() -> Scenario:
    lines = [
        Line("RM01", "room", "Room Rent - Single Room (incl. nursing)", 2, 5000),
        Line("DR01", "doctor", "Surgeon Fee - Arthroscopic ACL Reconstruction", 1, 120000),
        Line("DR02", "doctor", "Anaesthetist Fee", 1, 18000),
        Line("DR03", "doctor", "Consultant Visits - Orthopaedics", 2, 1500),
        Line("OT01", "ot", "Operation Theatre Charges", 1, 35000),
        Line("IM01", "implant", "Implants - Adjustable Loop Cortical Button + Bioabsorbable Interference Screw", 1, 42000),
        Line("OT02", "ot", "Arthroscopy Instrument Charges", 1, 8000),
        Line("PH01", "pharmacy", "Pharmacy - Medicines, Antibiotics, Analgesics", 1, 9800),
        Line("PT01", "misc", "In-patient Physiotherapy", 2, 1000),
        Line("CS01", "consumable", "Hinged Knee Brace (Long)", 1, 6500),
        Line("AM01", "ambulance", "Road Ambulance", 1, 3000),
    ]
    return Scenario(
        sid="S4", slug="s4-reasonable-customary-surgeon-fee",
        title="ACL surgery - surgeon fee halved as 'reasonable and customary'",
        summary="Cashless knee ligament reconstruction after a weekend football injury. The insurer restricted the Rs 1,20,000 surgeon fee to Rs 60,000 citing 'reasonable and customary charges', plus smaller policy-limit deductions. The fee cut needs the insurer's benchmark before it can be judged.",
        wording_id="AS-NIVA-2026",
        patient={"name": "Arjun Menon", "age": 34, "gender": "Male", "uhid": "NOH-2026-557120", "ip_no": "IP-26-3390", "relation": "Self"},
        policy={"policy_no": "NHI/AS/2025/0987765", "sum_insured": 300000, "cumulative_bonus": 0, "period": ("01-11-2025", "31-10-2026"), "first_inception": "01-11-2025", "history": "New policy (no prior insurance)", "peds_declared": "None", "city": "Bengaluru", "phone": "97400 00000"},
        admission={"hospital": "northstar", "claim_type": "Cashless", "doa": "12-08-2026", "dod": "14-08-2026", "doctor": "Dr. R. D'Souza, MS (Ortho), Fellowship Arthroscopy", "ward": "Single Room", "diagnosis": "Complete tear of anterior cruciate ligament, right knee (sports injury on 02-08-2026)", "procedure": "Arthroscopic ACL reconstruction with hamstring graft", "icd": "S83.511A"},
        lines=lines,
        deductions=[
            Deduction("DR01", 60000, "Reasonable & customary charges - surgeon fee restricted to Rs 60,000 as per prevailing rates in the locality", "needs_more_info",
                      "The policy's definition of Medical Expenses lets the insurer limit charges to what other hospitals/doctors in the same locality charge, but the letter gives no benchmark. Ask the insurer in writing for the data used; for a network hospital, also ask whether the fee matches the tariff/package agreed with the insurer. If they cannot show comparable local rates, escalate.",
                      ["NIVA-AS-3.29-MEDICAL-EXPENSES", "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE"], "moderate"),
            Deduction("OT02", 8000, "Subsumed into procedure charges - List III", "fair_ask_hospital_to_absorb",
                      "Arthroscopy instruments are List III in the policy's Annexure-A - part of procedure charges, so not paid separately. It was cashless at a network hospital, so you can ask the hospital to absorb it (a request, not an enforceable right).",
                      [np_id("ARTHROSCOPY AND ENDOSCOPY INSTRUMENTS")]),
            Deduction("CS01", 6500, "Non-payable item - List I", "fair", "Knee braces are List I (not covered).", [np_id("KNEE BRACES (LONG/ SHORT/ HINGED)")]),
            Deduction("AM01", 1000, "Road ambulance restricted to policy limit of Rs 2,000", "fair", "Road ambulance is capped at Rs 2,000 per hospitalisation (Section 4.1.1(v)).", ["NIVA-AS-4.1.1-AMBULANCE"]),
        ],
        letter={"type": "settlement", "date": "14-08-2026", "claim_no": "CLM-NHI-26-0851877", "received": "14-08-2026", "mode": "Cashless - final authorisation at discharge"},
        discharge={"history": "34-year-old male sustained a twisting injury to the right knee while playing recreational football on 02-08-2026. Knee swelling and instability. MRI (03-08-2026): complete ACL tear.", "course": "Underwent arthroscopic ACL reconstruction with ipsilateral hamstring autograft on 12-08-2026 under spinal anaesthesia. Post-op knee brace applied, physiotherapy started. Discharged ambulatory with walker support.", "advice": "Hinged knee brace locked in extension for 3 weeks. Physiotherapy protocol as explained. Tab. Aceclofenac-Paracetamol BD x 5 days. Suture removal after 14 days.", "comorbidities": "No known comorbidities"},
        extra_expected={
            "other_checks": [
                {"issue": "Hazardous / adventure sports exclusion (Excl09)", "verdict": "not_applicable",
                 "explanation": "Excl09 applies only to participation as a professional. The injury was recreational football, and the insurer did not invoke it - good to know in case it is raised in reply.",
                 "citations": ["NIVA-AS-7.6-SPORTS"]},
                {"issue": "30-day / specific waiting periods", "verdict": "not_applicable",
                 "explanation": "Policy is 9 months old, so the 30-day wait is over, and specific waiting periods do not apply to accidents.",
                 "citations": ["NIVA-AS-6.3-SPECIFIC"]},
            ],
        },
    )


def scenario_5() -> Scenario:
    lines = [
        Line("RM01", "room", "Room Rent - General Ward Twin Sharing (incl. nursing)", 4, 2500),
        Line("DR01", "doctor", "Consultant Visits - Dr. N. Hegde (Internal Medicine)", 8, 800),
        Line("PH01", "pharmacy", "Pharmacy - IV Fluids, Antipyretics, Medicines", 1, 11210),
        Line("IN01", "investigations", "Investigations - Dengue NS1, CBC x 6, LFT, Serum Electrolytes", 1, 7850),
        Line("MS01", "misc", "Attendant Food Charges", 1, 1800),
        Line("MS02", "misc", "Toiletries (soap, lotion, powder)", 1, 450),
        Line("MS03", "misc", "Television Charges", 4, 100),
        Line("MS04", "misc", "Laundry Charges", 1, 300),
        Line("MS05", "misc", "Admission Kit", 1, 850),
        Line("MS06", "misc", "Registration Charges", 1, 500),
    ]
    reimb = "Reimbursement at a non-network hospital: the claim is settled per policy terms, so this deduction is fair."
    return Scenario(
        sid="S5", slug="s5-all-deductions-fair",
        title="Dengue admission - every deduction is fair",
        summary="Reimbursement claim for dengue at a non-network hospital. Deductions are genuine List I-IV items and the 5% co-pay is computed correctly on the admissible amount. ClaimBack should say: nothing to challenge.",
        wording_id="AS-NIVA-2026",
        patient={"name": "Farhan Qureshi", "age": 41, "gender": "Male", "uhid": "GFH-2026-118470", "ip_no": "IP-8812/26", "relation": "Self"},
        policy={"policy_no": "NHI/AS/2026/0310552", "sum_insured": 200000, "cumulative_bonus": 10000, "period": ("01-03-2026", "28-02-2027"), "first_inception": "01-03-2024", "history": "Continuous with Nirmaan Health since 01-03-2024", "peds_declared": "None", "city": "Bengaluru", "phone": "96110 00000"},
        admission={"hospital": "greenfield", "claim_type": "Reimbursement", "doa": "25-08-2026", "dod": "29-08-2026", "doctor": "Dr. N. Hegde, MD (Internal Medicine)", "ward": "General Ward (Twin Sharing)", "diagnosis": "Dengue fever with thrombocytopenia", "procedure": "Medical management", "icd": "A90"},
        lines=lines,
        deductions=[
            Deduction("MS01", 1800, "Non-payable item - List I", "fair", "Food for attendants is List I (not covered).", [np_id("FOOD CHARGES (OTHER THAN PATIENT's DIET PROVIDED BY HOSPITAL)")]),
            Deduction("MS02", 450, "Non-payable item - List I (toiletries)", "fair", "Toiletries are List I (only prescribed medical pharmaceuticals are payable).",
                      [np_id("CREAMS POWDERS LOTIONS (Toiletries are not payable, only prescribed medical pharmaceuticals payable)")]),
            Deduction("MS03", 400, "Non-payable item - List I", "fair", "Television charges are List I (not covered).", [np_id("Television Charges")]),
            Deduction("MS04", 300, "Non-payable item - List I", "fair", "Laundry charges are List I (not covered).", [np_id("LAUNDRY CHARGES")]),
            Deduction("MS05", 850, "Subsumed into room charges - List II", "fair", "Admission kit is List II - part of room charges. " + reimb, [np_id("ADMISSION KIT")]),
            Deduction("MS06", 500, "Subsumed into cost of treatment - List IV", "fair", "Registration charges are List IV. " + reimb, [np_id("ADMISSION/REGISTRATION CHARGES")]),
        ],
        letter={"type": "settlement", "date": "12-09-2026", "claim_no": "CLM-NHI-26-0902214", "received": "02-09-2026", "mode": "Reimbursement - NEFT"},
        discharge={"history": "41-year-old male with high-grade fever, myalgia and retro-orbital pain for 3 days. NS1 antigen positive. Platelets 62,000/cumm on admission.", "course": "Managed with IV fluids and antipyretics; daily platelet monitoring (nadir 38,000/cumm on day 2, no bleeding, no transfusion required). Platelets 1,12,000/cumm at discharge. Afebrile for 48 hours.", "advice": "Oral fluids 3 L/day. Tab. Paracetamol 650 mg SOS. Repeat CBC after 3 days.", "comorbidities": "No known comorbidities"},
        extra_expected={
            "other_checks": [
                {"issue": "Co-payment computation", "verdict": "fair", "explanation": "5% co-pay applied on the admissible amount after deductions, as Section 9.5 requires.", "citations": ["NIVA-AS-9.5-COPAY"]},
                {"issue": "Settlement timeline", "verdict": "fair", "explanation": "Documents received 02-09-2026, settled 12-09-2026 = 10 days, within the 15 days in Section 9.6.", "citations": ["NIVA-AS-9.6-SETTLEMENT", "R-REIMBURSEMENT-SETTLEMENT-15-DAYS"]},
                {"issue": "Room rent", "verdict": "fair", "explanation": "Rs 2,500/day is within the eligible Rs 4,000/day (2% of Rs 2,00,000), so no proportionate deduction applies.", "citations": ["NIVA-AS-4.1-ROOM"]},
            ],
        },
    )


SCENARIOS = [scenario_1, scenario_2, scenario_3, scenario_4, scenario_5]

# Real decided cases (data/real_cases.json) worth showing next to each scenario, by case category.
SIMILAR_CASE_CATEGORIES = {
    "S1": ["non_payable_consumables"],
    "S2": ["proportionate_deduction", "room_rent_cap"],
    "S3": ["ped_non_disclosure"],
    "S4": ["reasonable_customary"],
    "S5": [],
}
REAL_CASES = json.loads((ROOT / "data/real_cases.json").read_text(encoding="utf-8"))


def similar_cases(sid: str) -> list[dict]:
    categories = SIMILAR_CASE_CATEGORIES[sid]
    return [
        {"case_id": c["id"], "category": c["category"], "forum": c["forum"], "decision_date": c["decision_date"],
         "decision": c["decision"], "insurer_reason": c["insurer_reason"], "reasoning": c["reasoning"],
         "decided_before_2024_health_rules": c["decided_before_2024_health_rules"], "source_url": c["source_url"]}
        for c in REAL_CASES if c["category"] in categories
    ]

# --------------------------------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------------------------------

BASE_CSS = """
@page { size: A4; margin: 14mm 14mm 18mm 14mm; @bottom-center { content: "__FOOTER__"; font-family: Arial, Helvetica, sans-serif; font-size: 7.5pt; color: #8a8a8a; } }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; color: #1b1b1b; margin: 0; }
h1 { font-size: 17pt; margin: 0; }
h2 { font-size: 12pt; margin: 14px 0 6px; text-transform: uppercase; letter-spacing: .04em; }
.muted { color: #555; }
.small { font-size: 8.5pt; }
.head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2.5px solid var(--accent); padding-bottom: 8px; }
.logo { width: 46px; height: 46px; border-radius: 10px; background: var(--accent); color: #fff; font-weight: 700; font-size: 18pt; display: flex; align-items: center; justify-content: center; margin-right: 10px; }
.brand { display: flex; align-items: center; }
.doc-title { text-align: center; font-size: 13pt; font-weight: 700; margin: 12px 0 8px; letter-spacing: .06em; }
table { width: 100%; border-collapse: collapse; }
.kv td { padding: 3px 6px; vertical-align: top; }
.kv td.k { color: #444; width: 23%; }
.kv td.v { font-weight: 600; width: 27%; }
.grid th, .grid td { border: 1px solid #9a9a9a; padding: 4px 6px; }
.grid th { background: #ececec; text-align: left; font-size: 9.5pt; }
.num { text-align: right; white-space: nowrap; }
.sub td { background: #f6f6f6; font-weight: 600; }
.total td { font-weight: 700; background: #e3e3e3; }
.box { border: 1px solid #9a9a9a; padding: 8px 10px; margin-top: 8px; }
.footer { display: none; text-align: center; font-size: 7.5pt; color: #8a8a8a; margin-top: 16px; }
@media screen { .footer { display: block; } }
.sign { margin-top: 28px; display: flex; justify-content: space-between; }
.stamp { border: 2px solid var(--accent); color: var(--accent); padding: 6px 12px; transform: rotate(-4deg); font-weight: 700; display: inline-block; }
"""


def page(title: str, accent: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>:root {{ --accent: {accent}; }} {BASE_CSS.replace("__FOOTER__", FOOTER)}</style></head>
<body>{body}<div class="footer">{FOOTER}</div></body></html>"""


def kv_rows(pairs: list[tuple[str, str]]) -> str:
    rows = []
    for i in range(0, len(pairs), 2):
        cells = ""
        for k, v in pairs[i:i + 2]:
            cells += f'<td class="k">{escape(k)}</td><td class="v">{escape(str(v))}</td>'
        rows.append(f"<tr>{cells}</tr>")
    return f'<table class="kv">{"".join(rows)}</table>'


def insurer_header(accent_title: str) -> str:
    return f"""<div class="head"><div class="brand"><div class="logo">N</div><div><h1>{INSURER['name']}</h1>
<div class="small muted">{INSURER['address']}<br>Toll free: {INSURER['tollfree']} | {INSURER['web']}</div></div></div>
<div class="small muted" style="text-align:right">IRDAI Regn. No. 000 (fictional)</div></div>
<div class="doc-title">{accent_title}</div>"""


def hospital_header(s: Scenario, title: str) -> str:
    h = s.hospital
    return f"""<div class="head"><div class="brand"><div class="logo">{h['name'][0]}</div><div><h1>{h['name']}</h1>
<div class="small muted">{h['address']}<br>Phone: 080-4000 0000 | {h['gstin']}</div></div></div>
<div class="small muted" style="text-align:right">NABH Accredited (fictional)<br>{'Network hospital - Nirmaan Health' if h['network'] else ''}</div></div>
<div class="doc-title">{title}</div>"""


def render_policy_schedule(s: Scenario) -> str:
    p, pt = s.policy, s.patient
    si = p["sum_insured"]
    room_cap = min(si * 2 // 100, 5000)
    icu_cap = min(si * 5 // 100, 10000)
    body = insurer_header("POLICY SCHEDULE - AROGYA SANJEEVANI POLICY")
    body += kv_rows([
        ("Policy number", p["policy_no"]), ("Product", "Arogya Sanjeevani Policy (Individual)"),
        ("Policy period", f"{p['period'][0]} to {p['period'][1]}"), ("Policyholder", pt["name"]),
        ("Address", f"{p['city']}, Karnataka"), ("Mobile", p["phone"]),
        ("First inception date", p["first_inception"]), ("Plan type", "Indemnity"),
    ])
    body += "<h2>Insured persons</h2>"
    body += f"""<table class="grid"><tr><th>Name</th><th>Relation</th><th>Age</th><th>Gender</th><th class="num">Sum insured (Rs)</th><th class="num">Cumulative bonus (Rs)</th><th>Pre-existing diseases declared</th></tr>
<tr><td>{pt['name']}</td><td>{pt['relation']}</td><td>{pt['age']}</td><td>{pt['gender']}</td><td class="num">{inr(si)}</td><td class="num">{inr(p['cumulative_bonus'])}</td><td>{p['peds_declared']}</td></tr></table>"""
    body += "<h2>Continuity of cover</h2>" + f'<div class="box">{escape(p["history"])}</div>'
    body += "<h2>Key benefits and limits</h2>"
    body += f"""<table class="grid">
<tr><td>Room rent, boarding, nursing</td><td>2% of sum insured, max Rs 5,000 per day - eligible: <b>Rs {inr(room_cap)} per day</b></td></tr>
<tr><td>ICU / ICCU</td><td>5% of sum insured, max Rs 10,000 per day - eligible: <b>Rs {inr(icu_cap)} per day</b></td></tr>
<tr><td>Cataract</td><td>25% of sum insured or Rs 40,000, whichever is lower, per eye per policy year</td></tr>
<tr><td>Modern treatments</td><td>Up to 50% of sum insured</td></tr>
<tr><td>Road ambulance</td><td>Up to Rs 2,000 per hospitalisation</td></tr>
<tr><td>Pre / post hospitalisation</td><td>30 days / 60 days</td></tr>
<tr><td>Co-payment</td><td>5% on every admissible claim</td></tr>
<tr><td>Waiting periods</td><td>30 days initial; 24/36 months specific; 36 months pre-existing diseases</td></tr>
<tr><td>Optional covers / add-ons</td><td>None opted</td></tr></table>"""
    body += '<p class="small muted">This schedule must be read with the policy wording. For grievances: ' + INSURER["gro_email"] + " | Bima Bharosa: bimabharosa.irdai.gov.in | Insurance Ombudsman, Bengaluru.</p>"
    return page("Policy Schedule", "#1f5fa8", body)


HEAD_LABELS = {"room": "Room & Boarding", "icu": "ICU / ICCU", "nursing": "Nursing", "doctor": "Professional Fees", "ot": "Operation Theatre / Procedure",
               "implant": "Implants", "pharmacy": "Pharmacy", "investigations": "Investigations", "consumable": "Medical Consumables", "misc": "Other Charges", "ambulance": "Ambulance"}


def render_bill(s: Scenario) -> str:
    a, pt = s.admission, s.patient
    body = hospital_header(s, "FINAL IN-PATIENT BILL")
    body += kv_rows([
        ("Bill no.", f"FB/{a['doa'][-4:]}/{pt['ip_no'][-4:]}"), ("Bill date", a["dod"]),
        ("Patient name", pt["name"]), ("Age / Gender", f"{pt['age']} / {pt['gender']}"),
        ("UHID", pt["uhid"]), ("IP no.", pt["ip_no"]),
        ("Date of admission", a["doa"]), ("Date of discharge", a["dod"]),
        ("Treating doctor", a["doctor"]), ("Ward / Room", a["ward"]),
        ("Payer", f"{INSURER['name']} - {a['claim_type']}"), ("Policy no.", s.policy["policy_no"]),
    ])
    rows = ""
    serial = 0
    order = ["room", "icu", "nursing", "doctor", "ot", "implant", "pharmacy", "investigations", "consumable", "misc", "ambulance"]
    for head in order:
        head_lines = [l for l in s.lines if l.head == head]
        if not head_lines:
            continue
        rows += f'<tr class="sub"><td colspan="6">{HEAD_LABELS[head]}</td></tr>'
        for l in head_lines:
            serial += 1
            rows += f'<tr><td>{serial}</td><td>{l.code}</td><td>{escape(l.description)}</td><td class="num">{l.qty}</td><td class="num">{inr(l.rate)}</td><td class="num">{inr(l.amount)}</td></tr>'
        rows += f'<tr><td colspan="5" class="num muted">Sub-total {HEAD_LABELS[head]}</td><td class="num">{inr(sum(l.amount for l in head_lines))}</td></tr>'
    total = sum(l.amount for l in s.lines)
    rows += f'<tr class="total"><td colspan="5" class="num">GROSS BILL AMOUNT (Rs)</td><td class="num">{inr(total)}</td></tr>'
    body += f"""<h2>Bill details</h2><table class="grid"><tr><th>#</th><th>Code</th><th>Description</th><th class="num">Qty</th><th class="num">Rate (Rs)</th><th class="num">Amount (Rs)</th></tr>{rows}</table>"""
    body += f'<div class="box small">Amount in words: Rupees {escape(words(total))} only. Healthcare services are exempt from GST. Itemised pharmacy annexure available on request.</div>'
    body += '<div class="sign"><div class="small">Patient / attendant signature</div><div class="small">Authorised signatory - Billing</div></div>'
    return page("Final Bill", "#0f766e", body)


def render_discharge(s: Scenario) -> str:
    a, pt, d = s.admission, s.patient, s.discharge
    body = hospital_header(s, "DISCHARGE SUMMARY")
    body += kv_rows([
        ("Patient name", pt["name"]), ("Age / Gender", f"{pt['age']} / {pt['gender']}"),
        ("UHID", pt["uhid"]), ("IP no.", pt["ip_no"]),
        ("Date of admission", a["doa"]), ("Date of discharge", a["dod"]),
        ("Consultant", a["doctor"]), ("Condition at discharge", "Stable"),
    ])
    for label, text in [("Final diagnosis", f"{a['diagnosis']} (ICD-10: {a['icd']})"), ("Procedure / treatment", a["procedure"]),
                        ("Past history / comorbidities", d["comorbidities"]), ("Presenting complaints & history", d["history"]),
                        ("Course in hospital", d["course"]), ("Advice on discharge", d["advice"])]:
        body += f"<h2>{label}</h2><div>{escape(text)}</div>"
    body += f'<div class="sign"><div></div><div class="small">{escape(a["doctor"])}<br>Reg. No. KMC-000000 (fictional)</div></div>'
    return page("Discharge Summary", "#0f766e", body)


def render_letter(s: Scenario) -> str:
    L, a, pt, p = s.letter, s.admission, s.patient, s.policy
    t = s.totals()
    ref = [("Claim no.", L["claim_no"]), ("Letter date", L["date"]), ("Policy no.", p["policy_no"]), ("Patient", pt["name"]),
           ("Hospital", s.hospital["name"]), ("Admission / discharge", f"{a['doa']} / {a['dod']}"),
           ("Claim type", L["mode"]), ("Documents received", L["received"])]
    grievance = f"""<div class="box small"><b>Not satisfied?</b> Write to our Grievance Redressal Officer at {INSURER['gro_email']} or call {INSURER['tollfree']}.
If your grievance is not resolved, you may register it on Bima Bharosa (bimabharosa.irdai.gov.in) or approach the Insurance Ombudsman under the Insurance Ombudsman Rules, 2017.</div>"""
    if L["type"] == "repudiation":
        body = insurer_header("REPUDIATION OF CLAIM")
        body += kv_rows(ref)
        body += f"<p>Dear {pt['name']},</p><p>We refer to your reimbursement claim for hospitalisation at {s.hospital['name']} for <b>{escape(a['diagnosis'])}</b>, for an amount of <b>Rs {inr(t['claimed'])}</b>.</p>"
        body += f'<h2>Reason for repudiation</h2><div class="box">{escape(L["reason"])}</div>'
        body += f"<p>In view of the above, we regret our inability to admit the claim. Amount claimed: Rs {inr(t['claimed'])}. Amount payable: <b>Rs 0.00</b>.</p>"
    else:
        body = insurer_header("CLAIM SETTLEMENT LETTER")
        body += kv_rows(ref)
        body += f"<p>Dear {pt['name']},</p><p>Your claim has been processed as per the terms and conditions of the policy. The details of the settlement are given below.</p>"
        body += "<h2>Settlement summary</h2>"
        body += f"""<table class="grid">
<tr><td>Total amount claimed</td><td class="num">{inr(t['claimed'])}</td></tr>
<tr><td>Less: deductions (see below)</td><td class="num">{inr(t['deducted'])}</td></tr>
<tr><td>Admissible amount</td><td class="num">{inr(t['admissible'])}</td></tr>
<tr><td>Less: co-payment @ {COPAY_PCT}% of admissible amount</td><td class="num">{inr(t['co_payment'])}</td></tr>
<tr class="total"><td>Amount {'authorised to hospital' if 'Cashless' in L['mode'] else 'paid to you by NEFT'}</td><td class="num">{inr(t['paid'])}</td></tr></table>"""
        body += f"""<h2>Deduction details</h2><table class="grid"><tr><th>#</th><th>Item</th><th class="num">Billed (Rs)</th><th class="num">Deducted (Rs)</th><th>Reason</th></tr>{letter_deduction_rows(s)}</table>"""
        if "Cashless" in L["mode"]:
            body += f"<p class='small'>Deducted amount and co-payment (Rs {inr(t['deducted'] + t['co_payment'])}) are payable by the patient directly to the hospital.</p>"
    body += grievance
    body += '<div class="sign"><div></div><div><div class="stamp">CLAIMS DEPT</div><div class="small" style="margin-top:6px">Authorised Signatory<br>Health Claims Team</div></div></div>'
    return page("Insurer Letter", "#1f5fa8", body)


def letter_deduction_rows(s: Scenario) -> str:
    """Rows as the insurer would print them: proportionate parts merged into one line."""
    rows, i = "", 0
    prop = [d for d in s.deductions if d.code is None]
    for d in s.deductions:
        if d.code is None:
            continue
        i += 1
        l = s.line(d.code)
        rows += f'<tr><td>{i}</td><td>{escape(l.description)}</td><td class="num">{inr(l.amount)}</td><td class="num">{inr(d.amount)}</td><td>{escape(d.insurer_reason)}</td></tr>'
    if prop:
        i += 1
        rows += f'<tr><td>{i}</td><td>Room rent and associated hospital charges</td><td class="num">-</td><td class="num">{inr(sum(d.amount for d in prop))}</td><td>{escape(prop[0].insurer_reason)}</td></tr>'
    return rows


ONES = "Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen Seventeen Eighteen Nineteen".split()
TENS = "_ _ Twenty Thirty Forty Fifty Sixty Seventy Eighty Ninety".split()


def words(n: int) -> str:
    def two(x):
        return ONES[x] if x < 20 else TENS[x // 10] + ("" if x % 10 == 0 else " " + ONES[x % 10])

    def three(x):
        h, r = divmod(x, 100)
        return (ONES[h] + " Hundred" + (" " + two(r) if r else "")) if h else two(r)

    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append(two(crore) + " Crore")
    if lakh:
        parts.append(two(lakh) + " Lakh")
    if thousand:
        parts.append(two(thousand) + " Thousand")
    if n:
        parts.append(three(n))
    return " ".join(parts) or "Zero"


# --------------------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------------------

def chrome(args: list[str]) -> None:
    subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", *args],
                   check=True, capture_output=True, timeout=120)


def html_to_pdf(html: str, pdf: Path, tmp: Path) -> None:
    src = tmp / (pdf.stem + ".html")
    src.write_text(html, encoding="utf-8")
    chrome([f"--print-to-pdf={pdf}", src.as_uri()])


def bill_photo(html: str, out: Path, tmp: Path) -> None:
    """Screenshot the bill and make it look like a phone photo: perspective skew, uneven light, blur, JPEG noise."""
    from PIL import Image, ImageDraw, ImageFilter

    src = tmp / "bill_photo.html"
    src.write_text(html, encoding="utf-8")
    shot = tmp / "bill_photo.png"
    chrome([f"--screenshot={shot}", "--window-size=1000,2600", "--hide-scrollbars", src.as_uri()])
    doc = Image.open(shot).convert("RGB")
    from PIL import ImageOps
    content = ImageOps.invert(doc).getbbox()  # crop the empty viewport below the bill
    if content:
        doc = doc.crop((0, 0, doc.width, min(doc.height, content[3] + 40)))
    w, h = doc.size
    canvas = Image.new("RGB", (w + 160, h + 160), (92, 74, 58))  # wooden table
    canvas.paste(doc, (80, 80))
    W, H = canvas.size
    rng = random.Random(7)
    # perspective: map output quad corners back into the source image
    top, bottom = rng.randint(8, 14), rng.randint(8, 14)  # same y offset on both sides keeps rows level
    quad = (rng.randint(30, 50), top, rng.randint(0, 15), H - bottom, W - rng.randint(0, 15), H - bottom, W - rng.randint(30, 50), top)
    photo = canvas.transform((W, H), Image.QUAD, quad, resample=Image.BICUBIC).rotate(-0.7, resample=Image.BICUBIC, expand=False, fillcolor=(92, 74, 58))
    shade = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(shade)
    for i in range(W):
        draw.line([(i, 0), (i, H)], fill=int(70 * (i / W) ** 1.6))
    photo = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), photo, shade)
    photo = photo.filter(ImageFilter.GaussianBlur(0.7)).resize((int(W * 0.9), int(H * 0.9)))
    photo.save(out, "JPEG", quality=72)


def expected_json(s: Scenario) -> dict:
    t = s.totals()
    ded = []
    for d in s.deductions:
        entry = {
            "line_code": d.code,
            "description": d.description or s.line(d.code).description,
            "billed": s.line(d.code).amount if d.code else None,
            "deducted": d.amount,
            "insurer_reason": d.insurer_reason,
            "expected_verdict": d.verdict,
            "explanation": d.explanation,
            "citations": d.citations,
        }
        if d.strength:
            entry["strength"] = d.strength
        ded.append(entry)
    challengeable = sum(d.amount for d in s.deductions if d.verdict == "challengeable")
    needs_info = sum(d.amount for d in s.deductions if d.verdict == "needs_more_info")
    hospital_dispute = sum(d.amount for d in s.deductions if d.verdict == "fair_ask_hospital_to_absorb")
    out = {
        "scenario_id": s.sid,
        "title": s.title,
        "summary": s.summary,
        "fictional": True,
        "evaluate_with_policy_wording": s.wording_id,
        "documents": ["policy_schedule.pdf", "hospital_bill.pdf", "discharge_summary.pdf", "insurer_letter.pdf"] + (["hospital_bill_photo.jpg"] if s.photo else []),
        "patient": s.patient,
        "policy": {**s.policy, "period": list(s.policy["period"])},
        "admission": {**s.admission, "hospital_name": s.hospital["name"], "network_hospital": s.hospital["network"]},
        "letter": {k: v for k, v in s.letter.items()},
        "claim_totals": t,
        "deductions": ded,
        "result": {
            "challengeable_amount": challengeable,
            "needs_more_info_amount": needs_info,
            "estimated_additional_payable_after_copay": int((challengeable) * (100 - COPAY_PCT) / 100),
            "upside_if_needs_more_info_resolved_after_copay": int(needs_info * (100 - COPAY_PCT) / 100),
            "ask_hospital_to_absorb_amount": hospital_dispute,
        },
    }
    if s.letter["type"] == "repudiation":
        out["result"] = {"claim_rejected": True}
    out.update(s.extra_expected)
    out["similar_real_cases"] = similar_cases(s.sid)
    return out


def line_items_json(s: Scenario) -> dict:
    return {
        "scenario_id": s.sid,
        "hospital": s.hospital["name"],
        "patient": s.patient["name"],
        "bill_date": s.admission["dod"],
        "gross_total": sum(l.amount for l in s.lines),
        "lines": [{"code": l.code, "head": l.head, "description": l.description, "qty": l.qty, "rate": l.rate, "amount": l.amount} for l in s.lines],
    }


def known_citation_ids() -> set[str]:
    ids = {it["id"] for it in NON_PAYABLE["items"]}
    ids |= {r["id"] for r in json.loads((ROOT / "data/rules_regulatory.json").read_text(encoding="utf-8"))}
    policy_terms = json.loads((ROOT / "data/policy_terms_arogya_sanjeevani.json").read_text(encoding="utf-8"))
    ids |= {c["id"] for pol in policy_terms["policies"] for c in pol["clauses"]}
    return ids


def check_citations(node, known: set[str], where: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("citations", "non_payable_citations"):
                missing = [c for c in value if c not in known]
                assert not missing, f"{where}: unknown citation ids {missing}"
            else:
                check_citations(value, known, where)
    elif isinstance(node, list):
        for value in node:
            check_citations(value, known, where)


def iso(d: str) -> str:
    """dd-mm-yyyy -> yyyy-mm-dd"""
    day, month, year = d.split("-")
    return f"{year}-{month}-{day}"


CONTINUOUS_COVER_START = {"S3": "15-06-2019"}  # ported policy: continuity from the previous insurer
CLAUSES_CITED = {"S3": ["Clause 10.1 (Disclosure of Information)", "Code Excl01 (Pre-Existing Diseases)"]}


def claim_input_json(s: Scenario) -> dict:
    """What extraction should read from this scenario's documents (backend ClaimInput schema)."""
    t = s.totals()
    p, a, pt, L = s.policy, s.admission, s.patient, s.letter
    deductions = []
    for d in s.deductions:
        if d.code is None:
            continue
        line = s.line(d.code)
        deductions.append({"line_code": d.code, "description": line.description, "billed": line.amount, "deducted": d.amount, "reason": d.insurer_reason})
    proportionate = [d for d in s.deductions if d.code is None]
    if proportionate:  # the letter prints one merged line, so extraction sees one
        deductions.append({"line_code": None, "description": "Room rent and associated hospital charges", "billed": None,
                           "deducted": sum(d.amount for d in proportionate), "reason": proportionate[0].insurer_reason})
    comorbidities = [] if s.discharge["comorbidities"].startswith("No known") else ["Type 2 Diabetes Mellitus", "Hypertension"]
    return {
        "policy": {
            "policy_number": p["policy_no"], "insurer_name": INSURER["name"], "product_name": "Arogya Sanjeevani Policy",
            "policy_wording_id": s.wording_id, "sum_insured": p["sum_insured"], "cumulative_bonus": p["cumulative_bonus"],
            "policy_period_start": iso(p["period"][0]), "policy_period_end": iso(p["period"][1]),
            "first_inception": iso(p["first_inception"]),
            "continuous_cover_start": iso(CONTINUOUS_COVER_START.get(s.sid, p["first_inception"])),
            "peds_declared": [], "optional_covers": [], "co_payment_pct": COPAY_PCT,
            "holder_name": pt["name"], "city": p["city"], "state": "Karnataka",
        },
        "admission": {
            "patient_name": pt["name"], "age": pt["age"], "gender": pt["gender"], "hospital_name": s.hospital["name"],
            "hospital_city": "Bengaluru", "network_hospital": s.hospital["network"],
            "claim_type": "cashless" if a["claim_type"] == "Cashless" else "reimbursement",
            "admission_date": iso(a["doa"]), "discharge_date": iso(a["dod"]), "diagnosis": a["diagnosis"],
            "procedure": a["procedure"], "is_accident": s.sid == "S4", "comorbidities": comorbidities,
        },
        "bill_lines": [{"code": l.code, "head": l.head, "description": l.description, "qty": l.qty, "rate": l.rate, "amount": l.amount} for l in s.lines],
        "decision": {
            "letter_type": L["type"], "letter_date": iso(L["date"]), "claim_number": L["claim_no"],
            "documents_received_date": iso(L["received"]), "amount_claimed": t["claimed"], "total_deducted": t["deducted"],
            "admissible_amount": None if L["type"] == "repudiation" else t["admissible"],
            "co_payment": None if L["type"] == "repudiation" else t["co_payment"], "amount_paid": t["paid"],
            "deductions": deductions, "repudiation_reason": L.get("reason"), "clauses_cited": CLAUSES_CITED.get(s.sid, []),
        },
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    known = known_citation_ids()
    index = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for build in SCENARIOS:
            s = build()
            folder = OUT / s.slug
            folder.mkdir(parents=True, exist_ok=True)
            html_to_pdf(render_policy_schedule(s), folder / "policy_schedule.pdf", tmp)
            bill_html = render_bill(s)
            html_to_pdf(bill_html, folder / "hospital_bill.pdf", tmp)
            html_to_pdf(render_discharge(s), folder / "discharge_summary.pdf", tmp)
            html_to_pdf(render_letter(s), folder / "insurer_letter.pdf", tmp)
            if s.photo:
                bill_photo(bill_html, folder / "hospital_bill_photo.jpg", tmp)
            exp = expected_json(s)
            check_citations(exp, known, s.sid)
            (folder / "expected.json").write_text(json.dumps(exp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            (folder / "line_items.json").write_text(json.dumps(line_items_json(s), indent=2) + "\n", encoding="utf-8")
            (folder / "claim_input.json").write_text(json.dumps(claim_input_json(s), indent=2) + "\n", encoding="utf-8")
            index.append({"scenario_id": s.sid, "folder": f"samples/{s.slug}", "title": s.title, "claim_totals": exp["claim_totals"], "result": exp["result"]})
            print(f"{s.sid} {s.slug}: {exp['claim_totals']} -> {exp['result']}")
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

"""Build data/non_payable_items.json + .csv - the List I-IV non-payable / subsumed items.

The lists originate in IRDAI/HLT/REG/CIR/193/07/2020 (22 July 2020), Annexure I and the Arogya Sanjeevani
standard wording's Annexure-A. That circular was superseded on 29 May 2024 (IRDAI/HLT/CIR/PRO/84/5/2024,
Annexure-6 item 1) and no 2024+ regulation carries the lists forward - they now bind only as contract terms
printed in policy wordings. So every item is also checked against current Arogya Sanjeevani wordings.

Usage: python scripts/build_non_payable_items.py
Requires: pdftotext on PATH.
"""

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "reference/superseded/irdai-master-circular-standardization-health-2020.pdf"
WORDINGS = {  # policy_id -> (file, first page, last page) of Annexure-A List I-IV
    "AS-NIVA-2026": (ROOT / "knowledge-base/policy-wordings/arogya-sanjeevani-niva-bupa-2026-27.pdf", 20, 23),
    "AS-STAR-2025": (ROOT / "knowledge-base/policy-wordings/arogya-sanjeevani-star-health-2025-26.pdf", 1, 99),
}
OUT_JSON = ROOT / "data/non_payable_items.json"
OUT_CSV = ROOT / "data/non_payable_items.csv"
SOURCE_URL = (
    "https://irdai.gov.in/documents/37343/366029/Master+Circular+on+Standardization+of+Health+Insurance+Products.pdf"
    "/40548736-71a8-1b76-e28d-0df899407e1e?version=1.2&t=1665033878433&download=true"
)

LIST_HEADER = re.compile(r"^\s*List\s+(I{1,3}|IV)\s*\W\s*(.+?)\s*$")
ITEM = re.compile(r"^\s*(\d{1,3})\s+(\S.*?)\s*$")
PAGE_FOOTER = re.compile(r"Page\s+(\d+)\s+of\s+155")

LIST_MEANING = {
    "I": {
        "annexure_i": "optional_item",
        "arogya_sanjeevani": "not_covered",
    },
    "II": "subsumed_into_room_charges",
    "III": "subsumed_into_procedure_charges",
    "IV": "subsumed_into_cost_of_treatment",
}

GUIDANCE = {
    "optional_item": (
        "Optional item: payable only if the claimant's policy has an add-on / optional cover for it (e.g. consumables "
        "cover). Only applies if the claimant's own policy wording prints this list - check the wording first."
    ),
    "not_covered": "Printed in the policy wording's Annexure-A List I (coverage not available). Deduction is fair.",
    "subsumed_into_room_charges": (
        "The policy wording says this is subsumed into room charges, so it is not paid as a separate line and a separate-line "
        "deduction is fair. At a network hospital you can ask the hospital to absorb it, but the 2020 IRDAI instruction that "
        "insurers stop hospitals billing these items was superseded in May 2024, so this is a request, not an enforceable right. "
        "Challenge only if the room charge itself was cut because of it."
    ),
    "subsumed_into_procedure_charges": (
        "The policy wording says this is subsumed into procedure charges, so a separate-line deduction is fair. At a network "
        "hospital you can ask the hospital to absorb it (a request, not an enforceable right since the 2020 circular was superseded)."
    ),
    "subsumed_into_cost_of_treatment": (
        "The policy wording says this is subsumed into cost of treatment (incl. diagnostics), so a separate-line deduction is fair. "
        "At a network hospital you can ask the hospital to absorb it (a request, not an enforceable right since the 2020 circular was superseded)."
    ),
}

VERBATIM_RULE = (
    "Insurers shall put in place measures to ensure that items which are part of room / surgical procedure / "
    "treatment (including diagnostics) as referred in the lists herein shall not be billed to the policyholders by "
    "the hospitals and every insurer shall inform or notify the same to the hospitals and the policyholders suitably."
)

# Common hospital-bill spellings, used by the matcher. Keys are canonical item names from the circular.
ALIASES = {
    "GLOVES": ["glove", "gloves sterile", "surgical gloves", "examination gloves", "nitrile gloves"],
    "MASK": ["face mask", "surgical mask", "n95 mask", "3 ply mask"],
    "NEBULIZER KIT": ["nebuliser kit", "nebulizer mask", "neb kit"],
    "NEBULISATION KIT": ["nebulisation set", "nebulization kit"],
    "THERMOMETER": ["digital thermometer"],
    "ECG ELECTRODES": ["ecg electrode", "electrodes"],
    "DIAPER OF ANY TYPE": ["diaper", "adult diaper", "diapers"],
    "SANITARY PAD": ["sanitary napkin", "maternity pad"],
    "CREPE BANDAGE": ["crepe", "elastic bandage"],
    "ATTENDANT CHARGES": ["attendant", "attendant bed", "companion charges"],
    "FOOD CHARGES (OTHER THAN PATIENT's DIET PROVIDED BY HOSPITAL)": ["attendant food", "visitor food", "canteen", "cafeteria"],
    "MINERAL WATER": ["water bottle", "packaged drinking water"],
    "LAUNDRY CHARGES": ["laundry", "linen charges"],
    "TELEPHONE CHARGES": ["telephone", "phone charges"],
    "TELEVISION CHARGES": ["tv charges", "television"],
    "MEDICAL RECORDS": ["medical record charges", "mrd charges", "case sheet copy"],
    "CERTIFICATE CHARGES": ["fitness certificate"],
    "PHOTOCOPIES CHARGES": ["photocopy", "xerox"],
    "VASOFIX SAFETY": ["vasofix", "iv cannula", "cannula"],
    "OXYGEN MASK": ["o2 mask"],
    "KIDNEY TRAY": ["kidney dish"],
    "WALKING AIDS CHARGES": ["walker", "walking stick", "crutches"],
    "PRIVATE NURSES CHARGES- SPECIAL NURSING CHARGES": ["special nursing", "private nurse"],
    "CREAMS POWDERS LOTIONS (Toiletries are not payable, only prescribed medical pharmaceuticals payable)": ["toiletries", "body lotion", "powder", "moisturiser"],
    "ANY KIT WITH NO DETAILS MENTIONED [DELIVERY KIT, ORTHOKIT, RECOVERY KIT, ETC]": ["delivery kit", "ortho kit", "recovery kit", "patient kit"],
    "ADMISSION KIT": ["admission kit", "welcome kit", "patient care kit"],
    "DOCUMENTATION CHARGES / ADMINISTRATIVE EXPENSES": ["documentation charges", "administrative charges", "admin charges"],
    "FILE OPENING CHARGES": ["file charges", "file opening"],
    "INCIDENTAL EXPENSES / MISC. CHARGES (NOT EXPLAINED)": ["miscellaneous", "misc charges", "incidental charges", "sundries"],
    "HOUSE KEEPING CHARGES": ["housekeeping", "housekeeping charges"],
    "AIR CONDITIONER CHARGES": ["ac charges"],
    "IM IV INJECTION CHARGES": ["injection charges", "iv injection charges", "im injection charges"],
    "PULSEOXYMETER CHARGES": ["pulse oximeter", "pulse oximetry charges", "spo2 monitoring"],
    "PATIENT IDENTIFICATION BAND / NAME TAG": ["id band", "wrist band", "name band"],
    "ENTRANCE PASS / VISITORS PASS CHARGES": ["visitor pass", "gate pass"],
    "DISCHARGE PROCEDURE CHARGES": ["discharge charges", "discharge processing"],
    "EXPENSES RELATED TO PRESCRIPTION ON DISCHARGE": ["discharge medicines", "take home medicines", "ttk medicines"],
    "SHOE COVER": ["shoe covers"],
    "CAPS": ["surgical cap", "head cap", "bouffant cap"],
    "GOWN": ["patient gown", "surgical gown", "disposable gown"],
    "TISSUE PAPER": ["tissue roll", "tissues", "wet wipes"],
    "BED PAN": ["bedpan"],
    "HAND WASH": ["handwash", "hand sanitiser", "hand sanitizer"],
    "DISINFECTANT LOTIONS": ["disinfectant"],
    "GAUZE": ["gauze pieces", "gauze swab", "sterile gauze"],
    "COTTON": ["cotton roll", "absorbent cotton"],
    "SURGICAL TAPE": ["micropore", "leucoplast", "adhesive tape"],
    "SURGICAL BLADES, HARMONICSCALPEL,SHAVER": ["surgical blade", "blade no", "harmonic scalpel"],
    "DISPOSABLES RAZORS CHARGES (for site preparations)": ["razor", "disposable razor"],
    "X-RAY FILM": ["xray film"],
    "WARD AND THEATRE BOOKING CHARGES": ["ot booking", "theatre booking"],
    "ARTHROSCOPY AND ENDOSCOPY INSTRUMENTS": ["arthroscopy instrument", "arthroscopy instruments", "endoscopy instrument", "endoscopy instruments"],
    "ORTHOBUNDLE, GYNAEC BUNDLE": ["ortho bundle", "gynaec bundle", "drape pack"],
    "ADMISSION/REGISTRATION CHARGES": ["registration charges", "registration fee", "admission charges", "admission fee"],
    "URINE BAG": ["uro bag", "urine collection bag"],
    "URINE CONTAINER": ["urine pot"],
    "ALCOHOL SWABES": ["alcohol swab", "alcohol swabs", "spirit swab"],
    "SCRUB SOLUTION/STERILLIUM": ["sterillium", "scrub solution", "hand rub"],
    "Glucometer & Strips": ["glucometer strips", "glucose strips", "grbs strips"],
    "NUTRITION PLANNING CHARGES - DIETICIAN CHARGES- DIET CHARGES": ["dietician charges", "dietitian charges", "diet consultation"],
    "HYDROGEN PEROXIDE\\SPIRIT\\ DISINFECTANTS ETC": ["hydrogen peroxide", "surgical spirit", "betadine solution"],
    "INFUSION PUMP– COST": ["infusion pump", "syringe pump"],
    "BIPAP MACHINE": ["bipap"],
    "CPAP/ CAPD EQUIPMENTS": ["cpap", "capd"],
    "ANTISEPTIC MOUTHWASH": ["mouthwash", "mouth wash"],
    "VACCINATION CHARGES": ["vaccine", "vaccination"],
}


def squash(text: str) -> str:
    # digits dropped too: some wordings' tables interleave serial numbers with item names
    return re.sub(r"[^A-Z]", "", text.upper()).replace("ISATION", "IZATION")


# Confirmed by reading the wording: printed with a typo, so exact matching cannot find it.
MANUAL_MATCHES = {("AS-STAR-2025", "BIPAP MACHINE"): "printed as 'PAP MACHINE'"}


def wording_pages(item: str) -> dict:
    """policy_id -> page where the item appears in that wording's annexure (None if not found)."""
    found = {}
    for policy_id, (pdf, first, last) in WORDINGS.items():
        pages = [squash(p) for p in pdf_pages(pdf, layout=False)[first - 1:last]]  # layout mode interleaves wrapped cells
        needle = squash(item)
        page = next((first + i for i, text in enumerate(pages) if needle in text), None)
        if page is None:  # item split across a page break
            page = next((first + i for i in range(len(pages) - 1) if needle in pages[i] + pages[i + 1]), None)
        if page is None and (policy_id, item) in MANUAL_MATCHES:
            page = MANUAL_MATCHES[(policy_id, item)]
        found[policy_id] = page
    return found


def pdf_pages(pdf: Path, layout: bool = True) -> list[str]:
    args = ["pdftotext", "-layout", str(pdf), "-"] if layout else ["pdftotext", str(pdf), "-"]
    text = subprocess.run(args, capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    return text.split("\f")


def norm(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", name.upper())


ALIAS_INDEX = {norm(k): v for k, v in ALIASES.items()}


def clean(name: str) -> str:
    name = name.replace("�", "–")
    return re.sub(r"\s+", " ", name).strip()


def parse_section(pages: list[str], first_page: int, last_page: int, schedule: str) -> list[dict]:
    """Parse List I-IV items from printed pages first_page..last_page (1-indexed, inclusive)."""
    items: list[dict] = []
    current_list = None
    current_title = None
    last_item = None
    for page_no in range(first_page, last_page + 1):
        for raw in pages[page_no - 1].splitlines():
            line = raw.rstrip()
            if not line.strip() or PAGE_FOOTER.search(line):
                continue
            header = LIST_HEADER.match(line)
            if header:
                current_list, current_title = header.group(1), clean(header.group(2))
                last_item = None
                continue
            if current_list is None:
                continue
            stripped = line.strip()
            if stripped.startswith(("Sl Item", "Sl ", "No", "Annexure")) or stripped in {"No.", "Item"}:
                continue
            if re.match(r"^\d+\.\s", stripped):  # numbered paragraph like "2. Where the costs ..."
                current_list, last_item = None, None
                continue
            match = ITEM.match(line)
            if match:
                meaning = LIST_MEANING[current_list]
                if isinstance(meaning, dict):
                    meaning = meaning[schedule]
                last_item = {
                    "schedule": schedule,
                    "list": current_list,
                    "list_title": current_title,
                    "sl_no": int(match.group(1)),
                    "item": clean(match.group(2)),
                    "treatment": meaning,
                    "page": page_no,
                }
                items.append(last_item)
            elif last_item and line.startswith("      "):  # wrapped continuation line
                last_item["item"] = clean(f"{last_item['item']} {stripped}")
    return items


def main() -> None:
    pages = pdf_pages(PDF)
    # Printed page numbers: Annexure I = pages 26-31; Arogya Sanjeevani Annexure-A = pages 136-139.
    annexure_i = parse_section(pages, 26, 31, "annexure_i")
    arogya = parse_section(pages, 136, 139, "arogya_sanjeevani")

    counts = {}
    for schedule_items in (annexure_i, arogya):
        for it in schedule_items:
            key = f"{it['schedule']}:List {it['list']}"
            counts[key] = counts.get(key, 0) + 1
    print(json.dumps(counts, indent=2))

    records = []
    for it in annexure_i + arogya:
        aliases = ALIAS_INDEX.get(norm(it["item"]), [])
        prefix = "AI" if it["schedule"] == "annexure_i" else "AS"
        records.append(
            {
                "id": f"NP-{prefix}-L{it['list']}-{it['sl_no']:03d}",
                **it,
                "aliases": aliases,
                "in_policy_wordings": wording_pages(it["item"]),
                "guidance": GUIDANCE[it["treatment"]],
            }
        )

    dataset = {
        "title": "IRDAI standard list of non-payable / subsumed items in health insurance",
        "source": {
            "binding_source": (
                "Annexure-A (List I-IV) printed in the claimant's policy wording - a contract term. 'in_policy_wordings' gives the "
                "page where each item appears in the current Arogya Sanjeevani wordings in data/policy_terms_arogya_sanjeevani.json."
            ),
            "origin": {
                "title": "Master Circular on Standardization of Health Insurance Products",
                "reference_no": "IRDAI/HLT/REG/CIR/193/07/2020",
                "date_issued": "2020-07-22",
                "file": "reference/superseded/irdai-master-circular-standardization-health-2020.pdf",
                "url": SOURCE_URL,
                "status": "superseded on 2024-05-29 by the Master Circular on Health Insurance Business (IRDAI/HLT/CIR/PRO/84/5/2024), Annexure-6 item 1",
                "pages": "annexure_i schedule: 26-31; arogya_sanjeevani schedule: 136-139",
            },
            "current_regulatory_hooks": [
                "R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS - deductions must trace to an exclusion written in the policy document",
                "R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE - a partial disallowance must cite the specific policy terms",
                "R-POLICY-MUST-STATE-SUBLIMITS-PROPORTIONATE-DEDUCTIONS",
            ],
        },
        "historical_rule": {
            "status": "superseded - do not cite as current law",
            "verbatim": VERBATIM_RULE,
            "page": 28,
        },
        "matching_notes": (
            "Items NOT on any list, e.g. prescribed medicines, implants, sutures, catheters, IV fluids, are not "
            "'non-payable' under these lists; if an insurer deducts one it must point to an exclusion or limit written in the "
            "policy document (R-NO-DEDUCTION-OUTSIDE-LISTED-EXCLUSIONS) and cite the clause (R-REJECTION-MUST-CITE-SPECIFIC-CLAUSE)."
        ),
        "counts": counts,
        "items": records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "schedule", "list", "sl_no", "item", "treatment", "aliases", "page"])
        for r in records:
            writer.writerow([r["id"], r["schedule"], r["list"], r["sl_no"], r["item"], r["treatment"], "|".join(r["aliases"]), r["page"]])
    print(f"wrote {len(records)} items -> {OUT_JSON.relative_to(ROOT)}, {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

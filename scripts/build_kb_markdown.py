"""Render curated Markdown pages for the Bedrock Knowledge Base from the structured data files.

Long PDFs chunk poorly (a policy wording buries the List I-IV tables in an annexure), so these short pages give
retrieval clean, self-contained chunks that always carry their citation.

Writes knowledge-base/curated/*.md (+ .metadata.json sidecars).
Usage: python scripts/build_kb_markdown.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "knowledge-base/curated"


def load(name: str):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write(slug: str, markdown: str, attrs: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.md").write_text(markdown.strip() + "\n", encoding="utf-8")
    (OUT / f"{slug}.md.metadata.json").write_text(json.dumps({"metadataAttributes": {"doc_type": "curated", **attrs}}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote knowledge-base/curated/{slug}.md")


def non_payable_pages() -> None:
    data = load("non_payable_items.json")
    origin = data["source"]["origin"]
    list_titles = {
        "I": "List I - Items for which coverage is not available in the policy",
        "II": "List II - Items that are to be subsumed into Room Charges",
        "III": "List III - Items that are to be subsumed into Procedure Charges",
        "IV": "List IV - Items that are to be subsumed into costs of treatment",
    }
    items = [i for i in data["items"] if i["schedule"] == "arogya_sanjeevani"]
    for lst, title in list_titles.items():
        rows = [i for i in items if i["list"] == lst]
        md = [f"# Non-payable items in health insurance: {title}", "",
              "Where this list is binding: it is printed as Annexure-A in Arogya Sanjeevani policy wordings (verified in the Niva Bupa 2026-27 "
              "and Star Health 2025-26 wordings) and in many other indemnity policy wordings. It binds as a contract term of the claimant's policy.", "",
              f"History: the list was standardised by IRDAI's {origin['title']} ({origin['reference_no']}, {origin['date_issued']}), which is "
              f"{origin['status']}. No 2024-2026 regulation or circular re-issues the list, so do not describe it as a current IRDAI rule - cite the policy wording.", "",
              f"How to treat a deduction of an item on this list: {rows[0]['guidance']}", "",
              data["matching_notes"], "",
              "| Sl | Item | Common bill wording | Niva Bupa AS 2026-27 page | Star Health AS 2025-26 page |", "|---|---|---|---|---|"]
        md += [f"| {r['sl_no']} | {r['item']} | {', '.join(r['aliases'])} | {r['in_policy_wordings']['AS-NIVA-2026']} | {r['in_policy_wordings']['AS-STAR-2025']} |" for r in rows]
        write(f"non-payable-list-{lst.lower()}", "\n".join(md), {"topic": "non_payable_items", "list": lst, "binding_source": "policy_wording_annexure_a"})


def policy_pages() -> None:
    data = load("policy_terms_arogya_sanjeevani.json")
    for pol in data["policies"]:
        md = [f"# {pol['product']} - key clauses for claim disputes", "",
              f"Insurer: {pol['insurer']}. UIN: {pol['uin']}. Policy wording file: {pol['file']}. Source: {pol['source_url']}", "",
              data["note"], ""]
        if pol.get("limits"):
            md += ["## Limits", "", "```json", json.dumps(pol["limits"], indent=2), "```", ""]
        if pol.get("proportionate_deduction"):
            pd = pol["proportionate_deduction"]
            md += ["## Proportionate (pro-rata) deduction", "",
                   f"Applies to: {', '.join(pd['applies_to'])}.", f"Does not apply to: {', '.join(pd['does_not_apply_to'])}.",
                   f"Clause: {pd['clause_ref']}, page {pd['page']}.", ""]
        for clause in pol["clauses"]:
            md += [f"## {clause['title']} ({clause['clause_ref']}, page {clause['page']})", "",
                   f"> {clause['verbatim_quote']}", "", f"Use when: {clause['use_when']}", f"Citation id: {clause['id']}", ""]
        write(f"policy-{pol['policy_id'].lower()}", "\n".join(md), {"topic": "policy_wording", "policy_id": pol["policy_id"], "uin": pol["uin"], "source_url": pol["source_url"]})


def rules_page() -> None:
    rules = load("rules_regulatory.json")
    if not rules:
        print("skip rules: data/rules_regulatory.json not found")
        return
    by_topic: dict[str, list] = {}
    for r in rules:
        by_topic.setdefault(r["topic"], []).append(r)
    for topic, group in sorted(by_topic.items()):
        md = [f"# IRDAI / regulatory rules: {topic.replace('_', ' ')}", ""]
        for r in group:
            md += [f"## {r['id']}", "", r["rule_summary"], "", f"> {r['verbatim_quote']}", "",
                   f"Source: {r['source_title']}, {r['clause_ref']}, page {r['page']} ({r['source_file']}). Effective: {r.get('effective_date')}.",
                   f"Use when: {r['use_when']}", f"Challenge strength: {r.get('challenge_strength')}", ""]
        write(f"rules-{topic.replace('_', '-')}", "\n".join(md), {"topic": topic})


def escalation_page() -> None:
    esc = load("escalation_path.json")
    if not esc:
        print("skip escalation: data/escalation_path.json not found")
        return
    write("escalation-path", "# How to escalate a health insurance claim dispute in India\n\n```json\n" + json.dumps(esc, indent=2, ensure_ascii=False) + "\n```", {"topic": "escalation"})


def main() -> None:
    non_payable_pages()
    policy_pages()
    rules_page()
    escalation_page()


if __name__ == "__main__":
    main()

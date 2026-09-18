"""Claude reviews the deductions the rule engine could not settle, researching with read-only tools.

Guardrails: Claude may only update findings the engine marked needs_more_info, and may only cite ids that exist in the
curated data - unknown ids are dropped, and an update left without citations is ignored.
"""

import json
from typing import Literal

from anthropic import beta_tool
from pydantic import BaseModel, Field

from ..config import settings
from ..engine.matcher import match_items
from ..knowledge import knowledge
from ..models import ClaimInput, Report
from . import check_refusal, client


class FindingUpdate(BaseModel):
    finding_id: str
    verdict: Literal["challengeable", "needs_more_info", "fair", "fair_ask_hospital_to_absorb"]
    strength: Literal["strong", "moderate", "weak"] | None
    amount_challengeable: float
    explanation: str = Field(description="Two or three plain-language sentences for the policyholder")
    citations: list[str] = Field(description="Ids returned by the tools, e.g. R-... rule ids, policy clause ids, NP-... item ids")


class ReviewResult(BaseModel):
    updates: list[FindingUpdate]
    note: str = Field(description="One sentence on what the review changed, for the report summary")


@beta_tool
def search_knowledge_base(query: str) -> str:
    """Search IRDAI regulations, the Arogya Sanjeevani policy wordings, the non-payable item lists and real Ombudsman / court decisions.

    Args:
        query: What to look for, e.g. "proportionate deduction ICU charges" or "rejection for late intimation".
    """
    if settings.knowledge_base_id:
        import boto3

        runtime = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
        result = runtime.retrieve(
            knowledgeBaseId=settings.knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 6}},
        )
        hits = [{"source": r.get("location", {}).get("s3Location", {}).get("uri"), "text": r["content"]["text"][:1500]}
                for r in result["retrievalResults"]]
    else:
        hits = [{"source": p.source, "title": p.title, "text": p.text} for p in knowledge().search(query, k=6)]
    return json.dumps(hits, ensure_ascii=False)


@beta_tool
def get_citation(citation_id: str) -> str:
    """Get the exact quote, source, clause and page for a rule id (R-...), policy clause id (e.g. NIVA-AS-8-MORATORIUM) or non-payable item id (NP-...).

    Args:
        citation_id: The id to resolve.
    """
    citation = knowledge().citation(citation_id)
    return citation.model_dump_json() if citation else json.dumps({"error": f"unknown id {citation_id}"})


@beta_tool
def list_rules(topic: str) -> str:
    """List current IRDAI rule ids and one-line summaries for a topic.

    Args:
        topic: One of moratorium, ped, waiting_period, proportionate_deduction, room_rent, claim_timeline, rejection_letter, cashless, non_disclosure, documents, grievance, ombudsman, bima_bharosa, other.
    """
    rules = [{"id": r["id"], "summary": r["rule_summary"], "use_when": r["use_when"]} for r in knowledge().rules.values() if r["topic"] == topic]
    return json.dumps(rules, ensure_ascii=False)


@beta_tool
def list_policy_clauses(policy_wording_id: str) -> str:
    """List the quoted clauses (ids, titles, when to use) of a supported policy wording.

    Args:
        policy_wording_id: e.g. AS-NIVA-2026 or AS-STAR-2025.
    """
    policy = knowledge().policy(policy_wording_id)
    if not policy:
        return json.dumps({"error": f"unsupported policy wording {policy_wording_id}"})
    return json.dumps([{"id": c["id"], "title": c["title"], "use_when": c["use_when"]} for c in policy["clauses"]], ensure_ascii=False)


@beta_tool
def lookup_non_payable_item(bill_description: str) -> str:
    """Check whether a hospital bill item is in the policy's Annexure-A List I-IV of non-payable / subsumed items.

    Args:
        bill_description: The line as printed on the bill.
    """
    matches = match_items(bill_description)
    return json.dumps([{"id": m.item_id, "item": m.item, "list": m.list, "treatment": m.treatment} for m in matches] or {"match": None})


SYSTEM = """You are ClaimBack's claims reviewer for Indian health insurance. A rule engine has already checked each \
deduction against the policy wording, IRDAI regulations and the policy's non-payable lists. You review only the \
deductions it could not settle (verdict needs_more_info).

For each one, research with the tools, then decide:
- challengeable: a specific clause, rule or list shows the deduction is wrong. Set amount_challengeable.
- fair: a specific clause, rule or list shows it is right.
- fair_ask_hospital_to_absorb: it is a List II-IV item on a cashless claim at a network hospital.
- needs_more_info: the insurer must show more before anyone can judge. Say exactly what to ask for.

Only cite ids you have seen in tool results. Do not rely on rules from memory - regulations changed in 2024. Decisions \
in real cases show how forums reason but are not binding law. When the evidence is thin, keep needs_more_info. Write \
explanations for a stressed family member: short sentences, no jargon, amounts in rupees."""


def review(claim: ClaimInput, report: Report) -> tuple[Report, bool]:
    """Returns (report, changed)."""
    open_findings = [f for f in report.deduction_findings if f.verdict == "needs_more_info"]
    if not open_findings:
        return report, False
    brief = {
        "policy_wording_id": report.policy_wording_id,
        "claim_type": claim.admission.claim_type,
        "network_hospital": claim.admission.network_hospital,
        "diagnosis": claim.admission.diagnosis,
        "procedure": claim.admission.procedure,
        "bill_lines": [line.model_dump() for line in claim.bill_lines],
        "findings_to_review": [f.model_dump(include={"id", "line_code", "description", "billed", "deducted", "insurer_reason", "explanation", "citations"})
                               for f in open_findings],
    }
    runner = client().beta.messages.tool_runner(
        model=settings.model_id,
        max_tokens=16000,
        max_iterations=15,
        system=SYSTEM,
        tools=[search_knowledge_base, get_citation, list_rules, list_policy_clauses, lookup_non_payable_item],
        messages=[{"role": "user", "content": "Review these findings:\n" + json.dumps(brief, default=str, ensure_ascii=False)}],
        output_format=ReviewResult,
    )
    final = runner.until_done()
    check_refusal(final)
    result: ReviewResult = final.parsed_output

    kb = knowledge()
    by_id = {f.id: f for f in report.deduction_findings}
    changed = False
    for update in result.updates:
        finding = by_id.get(update.finding_id)
        if not finding or finding.verdict != "needs_more_info":
            continue
        citations = [c for c in update.citations if kb.citation(c)]
        if not citations:
            continue
        finding.verdict = update.verdict
        finding.strength = update.strength
        finding.amount_challengeable = min(update.amount_challengeable, finding.deducted) if update.verdict == "challengeable" else 0
        finding.explanation = update.explanation
        finding.citations = citations
        for cid in citations:
            report.citations.setdefault(cid, kb.citation(cid))
        changed = True
    return report, changed

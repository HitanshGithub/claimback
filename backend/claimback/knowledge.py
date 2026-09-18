"""Loads the curated datasets (data/*.json) and resolves citation ids.

Also provides a small local keyword search over knowledge-base/ Markdown, used when no Bedrock
Knowledge Base is configured.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

from .config import settings
from .models import Citation

TOKEN = re.compile(r"[a-z0-9]+")

SHORT_SOURCES = {
    "irdai-master-circular-protection-of-policyholders-interests-2024.pdf": "IRDAI Master Circular on Protection of Policyholders' Interests, 2024",
    "irdai-protection-of-policyholders-interests-regulations-2024.pdf": "IRDAI (Protection of Policyholders' Interests) Regulations, 2024",
    "irdai-master-circular-health-insurance-2024.pdf": "IRDAI Master Circular on Health Insurance Business, 2024",
    "irdai-master-circular-health-insurance-2024-annexures.pdf": "IRDAI Master Circular on Health Insurance Business, 2024 (Annexures)",
    "irdai-insurance-products-regulations-2024.pdf": "IRDAI (Insurance Products) Regulations, 2024",
    "insurance-ombudsman-rules-2017-consolidated-2023.pdf": "Insurance Ombudsman Rules, 2017 (as amended)",
    "irdai-circular-ombudsman-self-contained-note-2026.pdf": "IRDAI circular on Ombudsman proceedings, July 2026",
}


def short_clause_ref(ref: str | None) -> str | None:
    """'Section 2, Chapter IV, para 16.3 (General Principles ...); see also ...' -> 'Section 2, Chapter IV, para 16.3'"""
    if not ref:
        return ref
    ref = ref.split(";")[0]
    return re.sub(r"\s\([^()]*[A-Za-z]{4,}[^()]*\)", "", ref).strip()


@dataclass
class Passage:
    source: str
    title: str
    text: str
    score: float


class Knowledge:
    def __init__(self, data_dir: Path, knowledge_dir: Path):
        self.data_dir = data_dir
        self.knowledge_dir = knowledge_dir

    def _load(self, name: str):
        return json.loads((self.data_dir / name).read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- datasets

    @cached_property
    def rules(self) -> dict[str, dict]:
        return {r["id"]: r for r in self._load("rules_regulatory.json")}

    @cached_property
    def policies(self) -> dict[str, dict]:
        return {p["policy_id"]: p for p in self._load("policy_terms_arogya_sanjeevani.json")["policies"]}

    @cached_property
    def policy_clauses(self) -> dict[str, tuple[dict, dict]]:
        """clause id -> (clause, policy)"""
        return {c["id"]: (c, p) for p in self.policies.values() for c in p["clauses"]}

    @cached_property
    def non_payable(self) -> dict:
        return self._load("non_payable_items.json")

    @cached_property
    def non_payable_items(self) -> dict[str, dict]:
        """Arogya Sanjeevani schedule (the lists printed in current policy wordings), by id."""
        return {i["id"]: i for i in self.non_payable["items"] if i["schedule"] == "arogya_sanjeevani"}

    @cached_property
    def cases(self) -> list[dict]:
        return self._load("real_cases.json")

    @cached_property
    def ombudsman_offices(self) -> list[dict]:
        offices = self._load("ombudsman_offices.json")
        return offices if isinstance(offices, list) else offices.get("offices", [])

    @cached_property
    def regulation_urls(self) -> dict[str, str]:
        """knowledge-base relative file path -> source_url, from the .metadata.json sidecars."""
        urls = {}
        for meta in self.knowledge_dir.glob("*/*.metadata.json"):
            attrs = json.loads(meta.read_text(encoding="utf-8")).get("metadataAttributes", {})
            if attrs.get("source_url"):
                rel = meta.relative_to(self.knowledge_dir.parent).as_posix().removesuffix(".metadata.json")
                urls[rel] = attrs["source_url"]
        return urls

    # ---------------------------------------------------------------- lookups

    def policy(self, policy_id: str | None) -> dict | None:
        return self.policies.get(policy_id) if policy_id else None

    def policy_clause_id(self, policy_id: str | None, suffix: str) -> str | None:
        """Find a clause of the given policy whose id ends with suffix, e.g. ('AS-NIVA-2026', '8-MORATORIUM')."""
        policy = self.policy(policy_id)
        if not policy:
            return None
        return next((c["id"] for c in policy["clauses"] if c["id"].endswith(suffix)), None)

    def wordings(self) -> list[dict]:
        return [{"id": p["policy_id"], "insurer": p["insurer"], "product": p["product"], "uin": p["uin"]} for p in self.policies.values()]

    def ombudsman_office_for(self, state: str | None, city: str | None) -> dict | None:
        needles = [s.lower() for s in (state, city) if s]
        for office in self.ombudsman_offices:
            haystack = " ".join(
                str(office.get(k, "")) for k in ("states", "union_territories", "jurisdiction_as_listed", "city")
            ).lower()
            if any(n in haystack for n in needles):
                return office
        return None

    def citation(self, cid: str) -> Citation | None:
        if cid in self.rules:
            r = self.rules[cid]
            return Citation(
                id=cid, kind="rule", title=r["rule_summary"], quote=r["verbatim_quote"],
                source=SHORT_SOURCES.get(Path(r["source_file"]).name, r["source_title"]), source_detail=r["source_title"],
                clause_ref=short_clause_ref(r.get("clause_ref")), page=r.get("page"), url=self.regulation_urls.get(r["source_file"]),
            )
        if cid in self.policy_clauses:
            c, p = self.policy_clauses[cid]
            return Citation(
                id=cid, kind="policy_clause", title=c["title"], quote=c["verbatim_quote"], source=p["product"],
                clause_ref=c["clause_ref"], page=c.get("page"), url=p.get("source_url"),
            )
        if cid in self.non_payable_items:
            i = self.non_payable_items[cid]
            return Citation(
                id=cid, kind="non_payable_item", title=f"{i['list_title']}: {i['item']}",
                quote=i["guidance"], source="Arogya Sanjeevani policy wording, Annexure-A",
                clause_ref=f"Annexure-A, List {i['list']}, item {i['sl_no']}", page=i["in_policy_wordings"].get("AS-NIVA-2026"),
            )
        return None

    # ---------------------------------------------------------------- local search

    @cached_property
    def _index(self) -> tuple[list[tuple[str, str, str, Counter]], Counter]:
        docs = []
        for md in sorted(self.knowledge_dir.glob("*/*.md")):
            text = md.read_text(encoding="utf-8")
            # split long pages on headings so hits stay focused
            for chunk in re.split(r"\n(?=## )", text):
                title = chunk.strip().splitlines()[0].lstrip("# ").strip() if chunk.strip() else md.stem
                docs.append((md.relative_to(self.knowledge_dir).as_posix(), title, chunk.strip(), Counter(TOKEN.findall(chunk.lower()))))
        df = Counter()
        for *_, counts in docs:
            df.update(counts.keys())
        return docs, df

    def search(self, query: str, k: int = 5) -> list[Passage]:
        """BM25 over knowledge-base Markdown (curated pages and real cases)."""
        docs, df = self._index
        terms = TOKEN.findall(query.lower())
        n = len(docs)
        avg_len = sum(sum(c.values()) for *_, c in docs) / max(n, 1)
        scored = []
        for source, title, text, counts in docs:
            length = sum(counts.values())
            score = 0.0
            for t in terms:
                if t not in counts:
                    continue
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                tf = counts[t]
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / avg_len))
            if score > 0:
                scored.append(Passage(source, title, text[:1500], score))
        return sorted(scored, key=lambda p: p.score, reverse=True)[:k]


@lru_cache(maxsize=1)
def knowledge() -> Knowledge:
    return Knowledge(settings.data_dir, settings.knowledge_dir)

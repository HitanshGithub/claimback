"""Match hospital-bill wording to the List I-IV non-payable items printed in the policy wording."""

import re
from dataclasses import dataclass
from functools import lru_cache

from ..knowledge import knowledge

GENERIC_WORDS = {"charges", "charge", "kit", "admission", "etc", "cost", "costs", "equipments", "machine", "expenses", "items"}


def normalize(text: str) -> str:
    text = re.sub(r"[^a-z ]", " ", text.lower())
    # crude singular form so "knee brace" matches "KNEE BRACES", "glove" matches "GLOVES"
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in text.split()]
    return " " + " ".join(words) + " "


@dataclass(frozen=True)
class ItemMatch:
    item_id: str
    item: str
    list: str
    treatment: str
    phrase: str


@lru_cache(maxsize=1)
def _phrases() -> list[tuple[str, dict]]:
    phrases = []
    for item in knowledge().non_payable_items.values():
        candidates = {item["item"]}
        # "DOCUMENTATION CHARGES / ADMINISTRATIVE EXPENSES" -> both halves; "FOOD CHARGES (OTHER THAN ...)" -> "FOOD CHARGES"
        for part in re.split(r"[/,()\[\]\\]| - |- ", item["item"]):
            part = part.strip()
            words = normalize(part).split()
            if len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 6 and words[0] not in GENERIC_WORDS):
                candidates.add(part)
        candidates.update(item["aliases"])
        for c in candidates:
            norm = normalize(c)
            if norm.strip():
                phrases.append((norm, item))
    return phrases


def match_items(description: str) -> list[ItemMatch]:
    """Best non-payable item match(es) for a bill description.

    The longest matching phrase wins. A description naming two items ("Gauze & Cotton") returns both when
    they are separate, non-overlapping phrases from the same list.
    """
    text = normalize(description)
    hits = [(len(phrase), phrase, item) for phrase, item in _phrases() if phrase in text]
    if not hits:
        return []
    hits.sort(key=lambda h: h[0], reverse=True)
    chosen: list[ItemMatch] = []
    used_spans: list[tuple[int, int]] = []
    for _, phrase, item in hits:
        start = text.find(phrase)
        span = (start + 1, start + len(phrase) - 1)  # phrases are space-padded; adjacent words must not count as overlap
        if any(span[0] < u[1] and u[0] < span[1] for u in used_spans):
            continue
        if any(m.item_id == item["id"] for m in chosen):
            continue
        if chosen and item["list"] != chosen[0].list:
            continue
        used_spans.append(span)
        chosen.append(ItemMatch(item["id"], item["item"], item["list"], item["treatment"], phrase.strip()))
    return chosen

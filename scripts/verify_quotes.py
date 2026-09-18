"""Check that every verbatim_quote in data/*.json really appears in its source PDF.

Walks each JSON file; a quote is checked against the nearest "source_file" / "file" key on the same
object or an ancestor. Comparison ignores case, whitespace and punctuation (PDF text extraction mangles
those), so a pass means the words are genuinely in the document. Also flags quotes whose recorded page is not one of the pages the quote appears on.

Usage: python scripts/verify_quotes.py [--fix-pages]
  --fix-pages  write the detected page number into quotes whose "page" is null or wrong
Requires: pdftotext on PATH.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_page_cache: dict[Path, list[str]] = {}


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def pages_of(pdf: Path) -> list[str]:
    if pdf not in _page_cache:
        raw = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, check=True).stdout
        _page_cache[pdf] = [squash(p) for p in raw.decode("utf-8", errors="replace").split("\f")]
    return _page_cache[pdf]


def find_pages(pdf: Path, quote: str) -> list[int]:
    """All pages containing the quote (circulars often repeat a paragraph across schedules)."""
    needle = squash(quote)
    pages = pages_of(pdf)
    hits = [i for i, page in enumerate(pages, 1) if needle in page]
    if not hits:  # quote may straddle a page break
        for i in range(1, len(pages)):
            if needle in pages[i - 1] + pages[i]:
                hits.append(i)
    return hits


def walk(node, source, results, path="$"):
    if isinstance(node, dict):
        source = node.get("source_file") or node.get("file") or source
        if node.get("verbatim_quote"):
            results.append((path, node, source))
        for key, value in node.items():
            walk(value, source, results, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            walk(value, source, results, f"{path}[{i}]")


def main() -> int:
    fix_pages = "--fix-pages" in sys.argv
    failures = 0
    for json_path in sorted((ROOT / "data").glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        results: list = []
        walk(data, None, results)
        if not results:
            continue
        ok = 0
        changed = False
        for path, node, source in results:
            label = node.get("id", path)
            if not source or not source.lower().endswith(".pdf"):
                print(f"  SKIP {json_path.name} {label}: no PDF source")
                continue
            pdf = ROOT / source
            if not pdf.exists():
                print(f"  FAIL {json_path.name} {label}: source file missing {source}")
                failures += 1
                continue
            pages = find_pages(pdf, node["verbatim_quote"])
            if not pages:
                print(f"  FAIL {json_path.name} {label}: quote not found in {source}")
                failures += 1
                continue
            ok += 1
            if "page" in node and node["page"] not in pages:
                print(f"  PAGE {json_path.name} {label}: recorded {node['page']}, found on {pages}")
                if fix_pages:
                    node["page"] = pages[0]
                    changed = True
        print(f"{json_path.name}: {ok}/{len(results)} quotes verified")
        if changed:
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

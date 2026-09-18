"""Download the third-party source documents that are not redistributed in this repository.

The datasets in data/ hold short quotes with page references; the full PDFs stay with their publishers. This script
fetches each one from its official URL (recorded in the knowledge-base metadata sidecars) so you can verify quotes
yourself with `python scripts/verify_quotes.py` and rebuild the datasets.

Usage: python scripts/download_sources.py
"""

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (ClaimBack source downloader)"}

# not in a metadata sidecar: superseded, kept only to rebuild the List I-IV datasets
EXTRA = {
    "reference/superseded/irdai-master-circular-standardization-health-2020.pdf":
        "https://irdai.gov.in/documents/37343/366029/Master+Circular+on+Standardization+of+Health+Insurance+Products.pdf"
        "/40548736-71a8-1b76-e28d-0df899407e1e?version=1.2&t=1665033878433&download=true",
}


def targets() -> dict[str, str]:
    """relative file path -> source url"""
    out = dict(EXTRA)
    for meta_path in sorted((ROOT / "knowledge-base").rglob("*.metadata.json")):
        attrs = json.loads(meta_path.read_text(encoding="utf-8")).get("metadataAttributes", {})
        url = attrs.get("source_url")
        target = meta_path.with_suffix("")  # drops ".json" -> "...pdf.metadata"
        target = target.with_suffix("")  # drops ".metadata" -> "...pdf"
        if url and target.suffix.lower() == ".pdf":
            out[target.relative_to(ROOT).as_posix()] = url
    return out


def main() -> None:
    downloaded = skipped = failed = 0
    for rel, url in sorted(targets().items()):
        path = ROOT / rel
        if path.exists():
            skipped += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=120) as response:
                path.write_bytes(response.read())
            print(f"downloaded {rel}")
            downloaded += 1
        except Exception as exc:
            print(f"FAILED    {rel}: {exc}\n          {url}")
            failed += 1
    print(f"\n{downloaded} downloaded, {skipped} already present, {failed} failed")
    if failed:
        print("If a link has moved, search for the document title on irdai.gov.in - DATASET.md lists every source.")


if __name__ == "__main__":
    main()

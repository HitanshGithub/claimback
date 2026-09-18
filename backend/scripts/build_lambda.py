"""Assemble backend/.build/lambda for `sam build`: the claimback package, its requirements, and the data it reads.

Knowledge-base PDFs are left out (they go to the Knowledge Base bucket); the Lambda only needs the curated Markdown,
metadata sidecars, data/*.json and the sample claim packs.

Usage: uv run python scripts/build_lambda.py
"""

import shutil
import subprocess
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
OUT = BACKEND / ".build" / "lambda"


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    shutil.copytree(BACKEND / "claimback", OUT / "claimback", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data", OUT / "data")
    shutil.copytree(ROOT / "samples", OUT / "samples")
    shutil.copytree(ROOT / "knowledge-base", OUT / "knowledge-base", ignore=shutil.ignore_patterns("*.pdf"))
    requirements = subprocess.run(
        ["uv", "export", "--no-dev", "--no-hashes", "--no-emit-project", "--format", "requirements-txt"],
        cwd=BACKEND, capture_output=True, text=True, check=True,
    ).stdout
    # boto3/botocore ship with the Lambda python3.13 runtime; bundling them wastes ~50 MB
    keep = [line for line in requirements.splitlines() if not line.split("==")[0].strip().lower() in {"boto3", "botocore", "s3transfer", "jmespath"}]
    (OUT / "requirements.txt").write_text("\n".join(keep) + "\n", encoding="utf-8")

    # Linux wheels for the Lambda runtime, so no Docker build is needed
    subprocess.run(
        ["uv", "pip", "install", "--target", str(OUT), "--requirement", str(OUT / "requirements.txt"),
         "--python-platform", "x86_64-manylinux2014", "--python-version", "3.13", "--no-installer-metadata", "--quiet"],
        cwd=BACKEND, check=True,
    )
    # keep *.dist-info: some packages (httpx2) read their version from installed metadata at import time
    for junk in OUT.rglob("__pycache__"):
        shutil.rmtree(junk, ignore_errors=True)
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"built {OUT} ({size / 1e6:.1f} MB with dependencies)")


if __name__ == "__main__":
    main()

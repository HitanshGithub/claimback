"""Build-free deploy of frontend/dist to AWS Amplify Hosting (manual deployment, no Git connection).

Creates the Amplify app and `main` branch on first run, then uploads dist/ as a zip and starts the deployment.
Re-runs just deploy the current dist/.

Usage:
  cd frontend && npm run build          (with VITE_API_BASE set to the API URL)
  uv run --project backend python infra/deploy_frontend.py --region ap-south-1
"""

import argparse
import io
import time
import urllib.request
import zipfile
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"
# send every path that isn't a real file to index.html, so React Router URLs work on refresh
SPA_RULE = {
    "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|png|txt|svg|woff|woff2|ttf|map|json|webp)$)([^.]+$)/>",
    "target": "/index.html",
    "status": "200",
}


def zip_dist() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(DIST.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(DIST).as_posix())
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--name", default="claimback")
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()
    if not (DIST / "index.html").exists():
        raise SystemExit(f"{DIST} has no index.html - run `npm run build` first")

    amplify = boto3.client("amplify", region_name=args.region)
    app = next((a for a in amplify.list_apps()["apps"] if a["name"] == args.name), None)
    if app:
        amplify.update_app(appId=app["appId"], customRules=[SPA_RULE])
        print(f"reusing app {app['appId']}")
    else:
        app = amplify.create_app(name=args.name, platform="WEB", customRules=[SPA_RULE],
                                 description="ClaimBack - check health insurance claim deductions")["app"]
        print(f"created app {app['appId']}")
    app_id = app["appId"]

    if not any(b["branchName"] == args.branch for b in amplify.list_branches(appId=app_id)["branches"]):
        amplify.create_branch(appId=app_id, branchName=args.branch, stage="PRODUCTION")
        print(f"created branch {args.branch}")

    deployment = amplify.create_deployment(appId=app_id, branchName=args.branch)
    payload = zip_dist()
    request = urllib.request.Request(deployment["zipUploadUrl"], data=payload, method="PUT",
                                     headers={"Content-Type": "application/zip"})
    with urllib.request.urlopen(request) as response:
        print(f"uploaded {len(payload) / 1e6:.1f} MB ({response.status})")
    job = amplify.start_deployment(appId=app_id, branchName=args.branch, jobId=deployment["jobId"])["jobSummary"]

    while job["status"] in ("PENDING", "RUNNING", "PROVISIONING"):
        time.sleep(5)
        job = amplify.get_job(appId=app_id, branchName=args.branch, jobId=job["jobId"])["job"]["summary"]
    print(f"deployment {job['status']}")
    print(f"\nSite: https://{args.branch}.{app_id}.amplifyapp.com")


if __name__ == "__main__":
    main()

"""Claim persistence: local JSON files for development, DynamoDB + S3 when deployed."""

import json
import shutil
import threading
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from .config import settings
from .models import Claim, ClaimDocument


def _dump(claim: Claim) -> str:
    data = json.loads(claim.model_dump_json())
    data["owner"] = claim.owner
    return json.dumps(data, ensure_ascii=False)


class Storage(Protocol):
    def save_claim(self, claim: Claim) -> None: ...
    def get_claim(self, claim_id: str) -> Claim | None: ...
    def list_claims(self) -> list[Claim]: ...
    def delete_claim(self, claim_id: str) -> None: ...
    def save_document(self, claim_id: str, doc: ClaimDocument, data: bytes) -> None: ...
    def read_document(self, claim_id: str, doc: ClaimDocument) -> bytes: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _dir(self, claim_id: str) -> Path:
        if not claim_id.replace("-", "").isalnum():
            raise ValueError("invalid claim id")
        return self.root / claim_id

    def save_claim(self, claim: Claim) -> None:
        folder = self._dir(claim.id)
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / "claim.json.tmp"
        with self._lock:
            tmp.write_text(_dump(claim), encoding="utf-8")
            tmp.replace(folder / "claim.json")

    def get_claim(self, claim_id: str) -> Claim | None:
        try:
            path = self._dir(claim_id) / "claim.json"
        except ValueError:
            return None
        if not path.exists():
            return None
        with self._lock:
            return Claim.model_validate_json(path.read_text(encoding="utf-8"))

    def list_claims(self) -> list[Claim]:
        claims = [c for p in self.root.glob("*/claim.json") if (c := self.get_claim(p.parent.name))]
        return sorted(claims, key=lambda c: c.created_at, reverse=True)

    def delete_claim(self, claim_id: str) -> None:
        folder = self._dir(claim_id)
        if folder.exists():
            shutil.rmtree(folder)

    def save_document(self, claim_id: str, doc: ClaimDocument, data: bytes) -> None:
        folder = self._dir(claim_id) / "documents"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{doc.kind}{Path(doc.filename).suffix.lower()}").write_bytes(data)

    def read_document(self, claim_id: str, doc: ClaimDocument) -> bytes:
        return (self._dir(claim_id) / "documents" / f"{doc.kind}{Path(doc.filename).suffix.lower()}").read_bytes()


class AwsStorage:
    """DynamoDB item per claim (the Claim JSON in attribute `doc`) and documents in S3."""

    def __init__(self, table_name: str, bucket_name: str, region: str):
        import boto3

        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        self.s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket_name

    def save_claim(self, claim: Claim) -> None:
        self.table.put_item(Item={"id": claim.id, "created_at": claim.created_at.isoformat(), "status": claim.status,
                                  "doc": _dump(claim)})

    def get_claim(self, claim_id: str) -> Claim | None:
        item = self.table.get_item(Key={"id": claim_id}).get("Item")
        return Claim.model_validate_json(item["doc"]) if item else None

    def list_claims(self) -> list[Claim]:
        items, kwargs = [], {}
        while True:
            page = self.table.scan(**kwargs)
            items += page["Items"]
            if "LastEvaluatedKey" not in page:
                break
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
        return sorted((Claim.model_validate_json(i["doc"]) for i in items), key=lambda c: c.created_at, reverse=True)

    def delete_claim(self, claim_id: str) -> None:
        self.table.delete_item(Key={"id": claim_id})
        listed = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=f"claims/{claim_id}/")
        for obj in listed.get("Contents", []):
            self.s3.delete_object(Bucket=self.bucket, Key=obj["Key"])

    def _key(self, claim_id: str, doc: ClaimDocument) -> str:
        return f"claims/{claim_id}/{doc.kind}{Path(doc.filename).suffix.lower()}"

    def save_document(self, claim_id: str, doc: ClaimDocument, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=self._key(claim_id, doc), Body=data, ContentType=doc.content_type,
                           ServerSideEncryption="AES256")

    def read_document(self, claim_id: str, doc: ClaimDocument) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=self._key(claim_id, doc))["Body"].read()


@lru_cache(maxsize=1)
def storage() -> Storage:
    if settings.storage == "aws":
        return AwsStorage(settings.table_name, settings.bucket_name, settings.aws_region)
    return LocalStorage(settings.local_store_dir)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

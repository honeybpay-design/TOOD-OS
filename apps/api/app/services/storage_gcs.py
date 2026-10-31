"""Opt-in London GCS storage with tenant-bound, generation-pinned original documents."""

import base64
import hashlib
import hmac
import re
import struct
import uuid

import google_crc32c
from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY, ConditionalRetryPolicy, is_generation_specified

from app.services.storage import StorageError

TIMEOUT = (5, 30)
SAFE_RETRY = ConditionalRetryPolicy(DEFAULT_RETRY.with_timeout(30), is_generation_specified, ["query_params"])
SHA256 = re.compile(r"[0-9a-f]{64}")


class NoDeleteBlob(storage.Blob):
    """The SDK's resumable checksum-error cleanup must not delete an object."""

    def delete(self, *args, **kwargs):
        raise StorageError("automatic object deletion is disabled; reconciliation requires review")


class GCSStore:
    def __init__(self, *, project: str, bucket_name: str, expected_project_number: str, client=None):
        if not project or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket_name):
            raise StorageError("GCS requires an explicit project and bucket")
        if not re.fullmatch(r"[1-9][0-9]{5,30}", expected_project_number):
            raise StorageError("GCS requires an explicit expected project number")
        self.bucket_name = bucket_name
        try:
            self.client = client if client is not None else storage.Client(project=project)
            self.bucket = self.client.get_bucket(bucket_name, timeout=TIMEOUT, retry=DEFAULT_RETRY.with_timeout(10))
            if self.bucket.location.upper() != "EUROPE-WEST2":
                raise StorageError("document storage must be in London europe-west2")
            if str(self.bucket.project_number) != expected_project_number:
                raise StorageError("document bucket belongs to an unexpected project")
            policy = self.bucket.iam_configuration
            if not policy.uniform_bucket_level_access_enabled or policy.public_access_prevention != "enforced":
                raise StorageError("document bucket requires uniform access and enforced public access prevention")
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("GCS metadata or credentials could not be verified") from exc

    def put(self, org_id: uuid.UUID, doc_id: uuid.UUID, data: bytes) -> str:
        if not isinstance(org_id, uuid.UUID) or not isinstance(doc_id, uuid.UUID) or not isinstance(data, bytes):
            raise ValueError("document storage requires generated UUIDs and original bytes")
        name = f"{org_id}/{doc_id}"
        digest = hashlib.sha256(data).hexdigest()
        checksum = base64.b64encode(struct.pack(">I", google_crc32c.value(data))).decode("ascii")
        blob = NoDeleteBlob(name, self.bucket)
        blob.metadata = {"sha256": digest}
        try:
            blob.upload_from_string(
                data,
                content_type="application/octet-stream",
                if_generation_match=0,
                checksum="crc32c",
                timeout=TIMEOUT,
                retry=SAFE_RETRY,
            )
            if not blob.generation or blob.generation < 1 or blob.size != len(data):
                raise StorageError("object generation or length was not confirmed")
            if blob.crc32c != checksum or (blob.metadata or {}).get("sha256") != digest:
                raise StorageError("stored object checksum or metadata did not match")
            return f"gcs:v1:{self.bucket_name}:{org_id}:{doc_id}:{blob.generation}:{digest}"
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("document upload did not complete safely") from exc

    def get(self, key: str, *, org_id: uuid.UUID | None = None, expected_sha256: str | None = None) -> bytes:
        if (
            not isinstance(org_id, uuid.UUID)
            or not isinstance(expected_sha256, str)
            or not SHA256.fullmatch(expected_sha256)
        ):
            raise ValueError("GCS reads require trusted organisation and database SHA-256")
        parts = key.split(":") if isinstance(key, str) else []
        if len(parts) != 7 or parts[:2] != ["gcs", "v1"] or parts[2] != self.bucket_name:
            raise ValueError("invalid or legacy storage pointer; reviewed migration is required")
        try:
            source_org, source_doc = uuid.UUID(parts[3]), uuid.UUID(parts[4])
        except ValueError as exc:
            raise ValueError("invalid storage pointer UUID") from exc
        if str(source_org) != parts[3] or str(source_doc) != parts[4] or source_org != org_id:
            raise ValueError("storage pointer does not belong to this organisation")
        if not re.fullmatch(r"[1-9][0-9]{0,19}", parts[5]) or int(parts[5]) > 2**64 - 1:
            raise ValueError("invalid object generation")
        if not SHA256.fullmatch(parts[6]) or not hmac.compare_digest(parts[6], expected_sha256):
            raise ValueError("storage pointer does not match the database content hash")
        generation = int(parts[5])
        blob = NoDeleteBlob(f"{source_org}/{source_doc}", self.bucket, generation=generation)
        try:
            data = blob.download_as_bytes(
                if_generation_match=generation, raw_download=True, checksum="crc32c", timeout=TIMEOUT, retry=SAFE_RETRY
            )
            if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), expected_sha256):
                raise StorageError("downloaded original does not match the database content hash")
            return data
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("document download did not complete safely") from exc

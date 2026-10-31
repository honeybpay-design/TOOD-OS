"""Object storage behind one small interface. The local-disk backend runs with no cloud account.

A cloud backend (for example Google Cloud Storage or S3) implements the same two methods; the rest of the
application never imports a cloud SDK. File names are never used in paths, only generated IDs.
"""

import hashlib
import hmac
import os
import pathlib
import uuid
from typing import Protocol

from app.core.config import settings


class StorageError(RuntimeError):
    """Storage could not be configured or completed safely; never fall back silently."""


class ObjectStore(Protocol):
    def put(self, org_id: uuid.UUID, doc_id: uuid.UUID, data: bytes) -> str: ...
    def get(self, key: str, *, org_id: uuid.UUID | None = None, expected_sha256: str | None = None) -> bytes: ...


class LocalStore:
    def __init__(self, root: str | None = None) -> None:
        self.root = pathlib.Path(root or settings.storage_dir).resolve()

    def put(self, org_id: uuid.UUID, doc_id: uuid.UUID, data: bytes) -> str:
        key = f"{org_id}/{doc_id}"
        path = (self.root / key).resolve()
        if self.root not in path.parents:  # defence in depth: never write outside the root
            raise ValueError("invalid storage key")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str, *, org_id: uuid.UUID | None = None, expected_sha256: str | None = None) -> bytes:
        if org_id is not None and (not isinstance(org_id, uuid.UUID) or not key.startswith(f"{org_id}/")):
            raise ValueError("storage key does not belong to this organisation")
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("invalid storage key")
        data = path.read_bytes()
        if expected_sha256 is not None and not hmac.compare_digest(hashlib.sha256(data).hexdigest(), expected_sha256):
            raise StorageError("stored content does not match the expected hash")
        return data


def get_store() -> ObjectStore:
    if settings.storage_backend == "local":
        if os.environ.get("K_SERVICE"):
            raise StorageError("Cloud Run requires an explicitly configured durable storage backend")
        return LocalStore()
    if settings.storage_backend == "gcs":
        try:
            from app.services.storage_gcs import GCSStore
        except ImportError as exc:
            raise StorageError("GCS backend dependency is unavailable") from exc

        return GCSStore(
            project=settings.gcp_project,
            bucket_name=settings.storage_gcs_bucket,
            expected_project_number=settings.storage_gcs_project_number,
        )
    raise StorageError("unknown storage backend")

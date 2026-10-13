"""Object storage behind one small interface. The local-disk backend runs with no cloud account.

A cloud backend (for example Google Cloud Storage or S3) implements the same two methods; the rest of the
application never imports a cloud SDK. File names are never used in paths, only generated IDs.
"""

import pathlib
import uuid
from typing import Protocol

from app.core.config import settings


class ObjectStore(Protocol):
    def put(self, org_id: uuid.UUID, doc_id: uuid.UUID, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...


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

    def get(self, key: str) -> bytes:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("invalid storage key")
        return path.read_bytes()


def get_store() -> ObjectStore:
    return LocalStore()

"""Standalone offline storage regressions; never imports the destructive conftest."""

import hashlib
import importlib
import os
import pathlib
import tempfile
import types
import unittest
import uuid
from unittest.mock import patch

from google.auth.credentials import AnonymousCredentials
from google.cloud import storage as sdk
from offline_guards import offline_application
from storage_http_fixture import SyntheticHTTP


class DurableStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tood-storage-unit-")
        self.addCleanup(self.temp.cleanup)
        self.settings = types.SimpleNamespace(
            storage_backend="local",
            storage_dir=self.temp.name,
            gcp_project="synthetic-no-cloud",
            storage_gcs_bucket="synthetic-documents",
            storage_gcs_project_number="999000111222",
        )
        self.enterContext(offline_application(self.settings))
        self.storage = importlib.import_module("app.services.storage")
        self.gcs = importlib.import_module("app.services.storage_gcs")
        # Config may already exist in the full API suite; bind the intended
        # synthetic settings locally and restore the module after each test.
        self.enterContext(patch.object(self.storage, "settings", self.settings))
        self.http = SyntheticHTTP()
        self.client = sdk.Client(project="synthetic-no-cloud", credentials=AnonymousCredentials(), _http=self.http)
        self.org, self.doc = uuid.uuid4(), uuid.uuid4()
        self.data = b"synthetic original"
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.store = self.new_store()

    def new_store(self):
        return self.gcs.GCSStore(
            project="synthetic-no-cloud",
            bucket_name="synthetic-documents",
            expected_project_number="999000111222",
            client=self.client,
        )

    def pointer(self):
        return self.store.put(self.org, self.doc, self.data)

    def test_legacy_local_roundtrip_and_traversal_protection(self):
        local = self.storage.LocalStore(self.temp.name)
        key = local.put(self.org, self.doc, self.data)
        self.assertEqual(local.get(key), self.data)
        self.assertEqual(local.get(key, org_id=self.org, expected_sha256=self.digest), self.data)
        with self.assertRaises(ValueError):
            local.get("../../outside")
        with self.assertRaises(ValueError):
            local.get(key, org_id=uuid.uuid4())
        with self.assertRaises(self.storage.StorageError):
            local.get(key, expected_sha256="0" * 64)

    def test_factory_local_uses_no_cloud(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(sdk, "Client", side_effect=AssertionError("Cloud factory forbidden")),
        ):
            self.assertIsInstance(self.storage.get_store(), self.storage.LocalStore)

    def test_cloud_run_refuses_local_fallback(self):
        with patch.dict(os.environ, {"K_SERVICE": "synthetic-api"}):
            with self.assertRaises(self.storage.StorageError):
                self.storage.get_store()
        self.assertEqual(list(pathlib.Path(self.temp.name).iterdir()), [])

    def test_unknown_backend_rejected(self):
        self.settings.storage_backend = "unknown"
        with self.assertRaises(self.storage.StorageError):
            self.storage.get_store()

    def test_factory_gcs_uses_explicit_bucket_and_project(self):
        self.settings.storage_backend = "gcs"
        with patch.object(sdk, "Client", return_value=self.client):
            result = self.storage.get_store()
        self.assertIsInstance(result, self.gcs.GCSStore)
        self.assertEqual(result.bucket.name, "synthetic-documents")

    def test_missing_configuration_rejected_before_sdk_credentials(self):
        self.settings.storage_backend = "gcs"
        for field in ["storage_gcs_bucket", "storage_gcs_project_number"]:
            old = getattr(self.settings, field)
            setattr(self.settings, field, "")
            with patch.object(sdk, "Client", side_effect=AssertionError("Credential access forbidden")):
                with self.assertRaises(self.storage.StorageError):
                    self.storage.get_store()
            setattr(self.settings, field, old)

    def test_wrong_region_rejected(self):
        self.http.bucket_metadata["location"] = "US"
        with self.assertRaises(self.storage.StorageError):
            self.new_store()
        self.assertEqual(self.http.objects, {})

    def test_wrong_project_rejected(self):
        self.http.bucket_metadata["projectNumber"] = "999000111223"
        with self.assertRaises(self.storage.StorageError):
            self.new_store()

    def test_nonuniform_access_rejected(self):
        self.http.bucket_metadata["iamConfiguration"]["uniformBucketLevelAccess"]["enabled"] = False
        with self.assertRaises(self.storage.StorageError):
            self.new_store()

    def test_unenforced_public_prevention_rejected(self):
        self.http.bucket_metadata["iamConfiguration"]["publicAccessPrevention"] = "inherited"
        with self.assertRaises(self.storage.StorageError):
            self.new_store()

    def test_pointer_binds_org_doc_generation_and_hash(self):
        pointer = self.pointer()
        self.assertEqual(
            pointer.split(":"), ["gcs", "v1", "synthetic-documents", str(self.org), str(self.doc), "1", self.digest]
        )
        self.assertEqual(self.http.objects[f"{self.org}/{self.doc}"]["data"], self.data)
        self.assertEqual(self.http.calls[-1]["query"]["ifGenerationMatch"], ["0"])

    def test_duplicate_cannot_overwrite_original(self):
        self.pointer()
        with self.assertRaises(self.storage.StorageError):
            self.store.put(self.org, self.doc, b"replacement")
        self.assertEqual(self.http.objects[f"{self.org}/{self.doc}"]["data"], self.data)

    def test_original_read_requires_tenant_and_database_hash(self):
        pointer = self.pointer()
        self.assertEqual(self.store.get(pointer, org_id=self.org, expected_sha256=self.digest), self.data)
        self.assertEqual(self.http.calls[-1]["query"]["generation"], ["1"])
        self.assertEqual(self.http.calls[-1]["query"]["ifGenerationMatch"], ["1"])

    def test_foreign_tenant_and_hash_fail_before_object_read(self):
        pointer = self.pointer()
        before = len(self.http.calls)
        for kwargs in [
            {},
            {"org_id": self.org},
            {"org_id": uuid.uuid4(), "expected_sha256": self.digest},
            {"org_id": self.org, "expected_sha256": "0" * 64},
        ]:
            with self.assertRaises(ValueError):
                self.store.get(pointer, **kwargs)
        self.assertEqual(len(self.http.calls), before)

    def test_malformed_other_bucket_and_legacy_pointers_rejected(self):
        pointer = self.pointer()
        before = len(self.http.calls)
        for bad in [
            "../../outside",
            f"{self.org}/{self.doc}",
            pointer.replace("synthetic-documents", "other-documents"),
            pointer.replace(":1:", ":0:"),
            pointer.replace(":1:", ":18446744073709551616:"),
            pointer.replace("gcs:v1:", "gcs:v2:"),
        ]:
            with self.assertRaises(ValueError):
                self.store.get(bad, org_id=self.org, expected_sha256=self.digest)
        self.assertEqual(len(self.http.calls), before)

    def test_stale_generation_cannot_read_a_different_version(self):
        pointer = self.pointer().replace(":1:", ":99:")
        with self.assertRaises(self.storage.StorageError):
            self.store.get(pointer, org_id=self.org, expected_sha256=self.digest)

    def test_corrupt_download_is_rejected(self):
        pointer = self.pointer()
        self.http.corrupt_download = True
        with self.assertRaises(self.storage.StorageError):
            self.store.get(pointer, org_id=self.org, expected_sha256=self.digest)

    def test_independent_adapter_can_read_same_pinned_original(self):
        pointer = self.pointer()
        self.assertEqual(self.new_store().get(pointer, org_id=self.org, expected_sha256=self.digest), self.data)
        # Shared synthetic HTTP state only: not a real-cloud replacement/durability proof.

    def test_large_valid_resumable_object_is_pinned(self):
        data = b"s" * (9 * 1024 * 1024)
        pointer = self.store.put(self.org, self.doc, data)
        self.assertEqual(
            self.store.get(pointer, org_id=self.org, expected_sha256=hashlib.sha256(data).hexdigest()), data
        )

    def test_checksum_failure_never_issues_sdk_automatic_delete(self):
        self.http.corrupt_upload_response = True
        with self.assertRaises(self.storage.StorageError):
            self.store.put(self.org, self.doc, b"s" * (9 * 1024 * 1024))
        self.assertEqual(sum(c["method"] == "DELETE" for c in self.http.calls), 0)
        self.assertEqual(
            len(self.http.objects), 1
        )  # Retained for reviewed reconciliation, never accepted as a document.

    def test_invalid_generated_identity_cannot_write(self):
        before = len(self.http.calls)
        with self.assertRaises(ValueError):
            self.store.put("../foreign", self.doc, self.data)
        with self.assertRaises(ValueError):
            self.store.put(self.org, "../outside", self.data)
        self.assertEqual(len(self.http.calls), before)

    def test_missing_sdk_is_a_storage_failure_without_local_fallback(self):
        import builtins

        self.settings.storage_backend = "gcs"
        original_import = builtins.__import__

        def no_sdk(name, *args, **kwargs):
            if name == "app.services.storage_gcs":
                raise ImportError("synthetic SDK absent")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=no_sdk):
            with self.assertRaises(self.storage.StorageError):
                self.storage.get_store()
        self.assertEqual(list(pathlib.Path(self.temp.name).iterdir()), [])

    def test_database_sha256_still_detects_corruption_when_wire_hash_is_absent(self):
        pointer = self.pointer()
        self.http.corrupt_download = True
        original_response = self.http.response

        def missing_checksum(method, url, *args, **kwargs):
            response = original_response(method, url, *args, **kwargs)
            if method == "GET" and "/o/" in url:
                response.headers.pop("X-Goog-Hash", None)
            return response

        with patch.object(self.http, "response", side_effect=missing_checksum):
            with self.assertRaisesRegex(self.storage.StorageError, "database content hash"):
                self.store.get(pointer, org_id=self.org, expected_sha256=self.digest)

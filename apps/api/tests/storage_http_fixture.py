"""Synthetic in-memory HTTP for exercising the real Google Storage SDK; never connects to GCP."""

import base64
import io
import json
import struct
from email import policy
from email.parser import BytesParser
from urllib.parse import parse_qs, unquote, urlparse

import google_crc32c
import requests
from urllib3.response import HTTPResponse


def crc(data):
    return base64.b64encode(struct.pack(">I", google_crc32c.value(data))).decode("ascii")


class SyntheticHTTP(requests.Session):
    def __init__(self):
        super().__init__()
        self.is_mtls = False
        self.bucket_metadata = {
            "name": "synthetic-documents",
            "location": "EUROPE-WEST2",
            "projectNumber": "999000111222",
            "iamConfiguration": {"publicAccessPrevention": "enforced", "uniformBucketLevelAccess": {"enabled": True}},
        }
        self.objects = {}
        self.calls = []
        self.pending = None
        self.corrupt_upload_response = False
        self.corrupt_download = False
        self.sequence = 0

    def response(self, method, url, status, body, headers=None):
        response = requests.Response()
        response.status_code = status
        response.url = url
        response.headers.update(headers or {})
        response._content = body if isinstance(body, bytes) else json.dumps(body).encode()
        response._content_consumed = True
        response.raw = HTTPResponse(
            body=io.BytesIO(response._content), headers=response.headers, status=status, preload_content=False
        )
        response.request = requests.Request(method, url).prepare()
        return response

    def request(self, method, url, data=None, headers=None, **kwargs):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.calls.append({"method": method, "path": parsed.path, "query": query})
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        if method == "GET" and parsed.path == "/storage/v1/b/synthetic-documents":
            return self.response(method, url, 200, self.bucket_metadata)
        if method == "POST" and query.get("uploadType") == ["resumable"]:
            self.pending = (json.loads(data), query)
            return self.response(method, url, 200, {}, {"Location": "https://synthetic-upload.invalid/session/1"})
        if method == "POST" and query.get("uploadType") == ["multipart"]:
            content_type = headers["content-type"]
            if isinstance(content_type, bytes):
                content_type = content_type.decode()
            message = BytesParser(policy=policy.default).parsebytes(
                ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + data
            )
            parts = list(message.iter_parts())
            metadata = json.loads(parts[0].get_payload(decode=True))
            payload = parts[1].get_payload(decode=True)
            if "crc32c" in metadata and metadata["crc32c"] != crc(payload):
                return self.response(
                    method, url, 400, {"error": {"code": 400, "message": "synthetic checksum mismatch"}}
                )
            return self.accept(method, url, metadata, payload, query)
        if method == "PUT" and parsed.netloc == "synthetic-upload.invalid":
            metadata, original_query = self.pending
            return self.accept(method, url, metadata, bytes(data), original_query)
        if "/o/" in parsed.path:
            name = unquote(parsed.path.split("/o/", 1)[1])
            entry = self.objects.get(name)
            if entry is None:
                return self.response(method, url, 404, {"error": {"code": 404, "message": "synthetic missing object"}})
            if query.get("ifGenerationMatch", [str(entry["generation"])])[0] != str(entry["generation"]):
                return self.response(
                    method, url, 412, {"error": {"code": 412, "message": "synthetic generation mismatch"}}
                )
            if method == "DELETE":
                del self.objects[name]
                return self.response(method, url, 204, b"")
            if method == "GET":
                payload = entry["data"] + (b" altered" if self.corrupt_download else b"")
                return self.response(
                    method,
                    url,
                    200,
                    payload,
                    {
                        "X-Goog-Hash": "crc32c=" + crc(entry["data"]),
                        "X-Goog-Generation": str(entry["generation"]),
                        "Content-Length": str(len(payload)),
                    },
                )
        raise AssertionError("Unexpected synthetic request: " + method + " " + url)

    def accept(self, method, url, metadata, payload, query):
        name = metadata["name"]
        if query.get("ifGenerationMatch") == ["0"] and name in self.objects:
            return self.response(
                method, url, 412, {"error": {"code": 412, "message": "synthetic object already exists"}}
            )
        self.sequence += 1
        self.objects[name] = {"generation": self.sequence, "data": payload}
        return self.response(
            method,
            url,
            200,
            {
                "name": name,
                "bucket": "synthetic-documents",
                "generation": str(self.sequence),
                "size": str(len(payload)),
                "crc32c": crc(b"wrong" if self.corrupt_upload_response else payload),
                "metadata": metadata.get("metadata", {}),
            },
        )

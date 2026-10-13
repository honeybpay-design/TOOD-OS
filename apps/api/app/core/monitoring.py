"""Cloud Monitoring integration. Sends metrics and logs to Google Cloud Monitoring."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class CloudMonitor:
    """Sends metrics and logs to Google Cloud Monitoring. Degrades gracefully if SDK unavailable."""

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self._client = None
        self._log_client = None
        self._available = False
        self._sdk_present = False
        # Only check if the SDK is importable; defer client creation to first write
        try:
            import google.cloud.logging  # noqa: F401 — probe import only
            import google.cloud.monitoring_v3  # noqa: F401 — probe import only

            self._sdk_present = True
        except ImportError:
            logger.warning("google-cloud-monitoring not installed; Cloud Monitoring disabled")

    def _ensure_client(self) -> bool:
        """Lazily initialise the GCP clients. Returns True when ready."""
        if self._available:
            return True
        if not self._sdk_present:
            return False
        # Do NOT short-circuit on self._client here: a previous attempt may have
        # assigned _client but failed before setting _monitoring_v3 or _available,
        # leaving the object in a partial state.  Let the try block re-run so all
        # three attributes are set atomically before _available becomes True.
        try:
            from google.cloud import logging as cloud_logging
            from google.cloud import monitoring_v3

            monitoring_v3_mod = monitoring_v3
            client = monitoring_v3.MetricServiceClient()
            log_client = cloud_logging.Client(project=self.project_id)
            # Assign atomically — only after all three succeed
            self._monitoring_v3 = monitoring_v3_mod
            self._client = client
            self._log_client = log_client
            self._available = True
            return True
        except Exception as e:
            logger.warning("Cloud Monitoring init failed: %s", e)
            return False

    def _write_metric(self, metric_type: str, value: float, labels: dict[str, str]) -> None:
        if not self._ensure_client():
            return
        try:
            project_name = f"projects/{self.project_id}"
            series = self._monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/tood/{metric_type}"
            for k, v in labels.items():
                series.metric.labels[k] = str(v)
            series.resource.type = "global"
            point = self._monitoring_v3.Point()
            point.value.double_value = float(value)
            now = time.time()
            point.interval.end_time.seconds = int(now)
            point.interval.end_time.nanos = int((now % 1) * 1e9)
            series.points = [point]
            self._client.create_time_series(name=project_name, time_series=[series])
        except Exception as e:
            logger.warning("Metric write failed (%s): %s", metric_type, e)

    def record_ai_call(self, model_id: str, latency_ms: float, tokens_used: int, success: bool) -> None:
        self._write_metric(
            "ai_call_latency_ms",
            latency_ms,
            {
                "model_id": model_id,
                "success": str(success).lower(),
            },
        )
        logger.info("ai_call model=%s latency_ms=%.1f tokens=%d success=%s", model_id, latency_ms, tokens_used, success)

    def record_api_request(self, endpoint: str, method: str, status_code: int, latency_ms: float) -> None:
        self._write_metric(
            "api_request_latency_ms",
            latency_ms,
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": str(status_code),
            },
        )

    def record_export(self, org_id: str, tender_id: str, success: bool) -> None:
        self._write_metric(
            "export_count",
            1.0,
            {
                "org_id": str(org_id),
                "tender_id": str(tender_id),
                "success": str(success).lower(),
            },
        )
        logger.info("export org=%s tender=%s success=%s", org_id, tender_id, success)

    def health_ping(self) -> None:
        self._write_metric("health_ping", 1.0, {"service": "tood-os-api"})
        logger.info("health_ping project=%s available=%s", self.project_id, self._available)


_monitor: CloudMonitor | None = None


def get_monitor() -> CloudMonitor:
    global _monitor
    if _monitor is None:
        from app.core.config import settings

        _monitor = CloudMonitor(project_id=settings.gcp_project)
    return _monitor

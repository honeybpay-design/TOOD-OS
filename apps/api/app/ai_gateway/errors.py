"""Typed failure for unavailable AI generation; never contains provider diagnostics."""


class AIProviderUnavailable(RuntimeError):
    """Generation did not succeed; no alternate model was selected implicitly."""

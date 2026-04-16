"""Runtime debug flags for IFC diagnostics (file logs, verbose console)."""

import os

# Production default: off. Set CAMUNLP_DEBUG=1 (or true/yes) for developer diagnostics.
DEBUG_LOG_ENABLED = os.environ.get("CAMUNLP_DEBUG", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

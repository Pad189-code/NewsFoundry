"""Rate limiting (SlowAPI). Disabled when DISABLE_RATE_LIMIT is set (e.g. in tests)."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("DISABLE_RATE_LIMIT", "").lower()
    not in ("1", "true", "yes"),
)

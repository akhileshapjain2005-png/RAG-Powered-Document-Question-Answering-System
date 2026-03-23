"""Shared rate limiter configuration."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "200/minute")],
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
)

"""Thin wrapper around the existing firebase_service module.

Use get_service() to obtain the singleton Firestore service.
"""

from typing import Any


def get_service() -> Any:
    # Lazy import to avoid heavy imports at module import time
    from bot.firebase_service import get_firebase_service as _get_fb

    return _get_fb()



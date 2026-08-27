"""trustcore: the standalone trust primitives SIMFORGE is built on.

A small, dependency-light package: tamper-evident audit spine, JWT/SSRF
security primitives, and an in-process event bus. SIMFORGE owns this code;
it does not import any other product.
"""
from __future__ import annotations

from .spine import Spine, SpineConfig, SpineError
from .security import (
    AuthError,
    WeakSecretError,
    require_strong_secret,
    make_token,
    verify_token,
    is_ssrf_safe,
    get_logger,
)
from .backbone import ControlEvent, EventBus, register_subsystem, all_subsystems, reset_registry

__all__ = [
    "Spine", "SpineConfig", "SpineError",
    "AuthError", "WeakSecretError", "require_strong_secret", "make_token",
    "verify_token", "is_ssrf_safe", "get_logger",
    "ControlEvent", "EventBus", "register_subsystem", "all_subsystems", "reset_registry",
]

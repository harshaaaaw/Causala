"""trustcore: the standalone trust primitives SIMFORGE is built on.

A small, dependency-light package: tamper-evident audit spine, JWT/SSRF
security primitives, and an in-process event bus. SIMFORGE owns this code;
it does not import any other product.
"""
from __future__ import annotations

from .backbone import ControlEvent, EventBus, all_subsystems, register_subsystem, reset_registry
from .security import (
    AuthError,
    WeakSecretError,
    get_logger,
    is_ssrf_safe,
    make_token,
    require_strong_secret,
    verify_token,
)
from .spine import Spine, SpineConfig, SpineError

__all__ = [
    "AuthError",
    "ControlEvent",
    "EventBus",
    "Spine",
    "SpineConfig",
    "SpineError",
    "WeakSecretError",
    "all_subsystems",
    "get_logger",
    "is_ssrf_safe",
    "make_token",
    "register_subsystem",
    "require_strong_secret",
    "reset_registry",
    "verify_token",
]

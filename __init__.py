"""Persistent key-value store using SQLite with dict-like interface."""

from .vault import Vault, VaultError, set_root_path, set_logger

__all__ = ["Vault", "VaultError", "set_root_path", "set_logger"]

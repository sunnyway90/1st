"""Minimal plugin registry — add modules without touching the core CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from litework.core.store import Store


@dataclass
class Module:
    """A pluggable feature pack."""

    name: str
    description: str
    register_commands: Callable  # (subparsers, store_factory) -> None
    required: bool = False
    aliases: list[str] = field(default_factory=list)


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}

    def register(self, module: Module) -> None:
        if module.name in self._modules:
            raise ValueError(f"module already registered: {module.name}")
        self._modules[module.name] = module

    def get(self, name: str) -> Module | None:
        return self._modules.get(name)

    def all(self) -> list[Module]:
        return sorted(self._modules.values(), key=lambda m: m.name)

    def names(self) -> list[str]:
        return [m.name for m in self.all()]


_REGISTRY: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    """Return the process-wide registry, loading built-in modules once."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModuleRegistry()
        _load_builtin_modules(_REGISTRY)
    return _REGISTRY


def reset_registry() -> None:
    """Test helper to clear the singleton."""
    global _REGISTRY
    _REGISTRY = None


def _load_builtin_modules(registry: ModuleRegistry) -> None:
    from litework.modules import org, progress, schedule

    for mod in (org, schedule, progress):
        registry.register(mod.MODULE)


def ensure_module_enabled(store: Store, name: str) -> None:
    """Raise if a non-required module is disabled for this workspace."""
    module = get_registry().get(name)
    if module and module.required:
        return
    if not store.is_module_enabled(name, default=True):
        raise RuntimeError(
            f"module '{name}' is disabled. Enable it with: "
            f"litework module enable {name}"
        )

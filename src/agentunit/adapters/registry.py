"""Adapter registry — discovers and manages framework adapters."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentunit.adapters.base import AgentAdapter

_adapters: dict[str, AgentAdapter] = {}
_discovered = False


def _discover() -> None:
    """Discover and register built-in adapters + entry_points adapters."""
    global _discovered
    if _discovered:
        return

    # Register built-in adapters
    from agentunit.adapters.generic_python.adapter import GenericPythonAdapter
    from agentunit.adapters.langchain.adapter import LangChainAdapter
    from agentunit.adapters.pm_agent.adapter import PmAgentAdapter

    for adapter_cls in (GenericPythonAdapter, LangChainAdapter, PmAgentAdapter):
        adapter = adapter_cls()
        _adapters[adapter.name] = adapter

    # Discover third-party adapters via entry_points
    for ep in entry_points(group="agentunit.adapters"):
        if ep.name not in _adapters:
            adapter_cls = ep.load()
            adapter = adapter_cls() if isinstance(adapter_cls, type) else adapter_cls
            _adapters[adapter.name] = adapter

    _discovered = True


def register(adapter: AgentAdapter) -> None:
    """Manually register an adapter."""
    _adapters[adapter.name] = adapter


def get(framework: str) -> AgentAdapter:
    """Get adapter by framework name. Raises KeyError if not found."""
    _discover()
    if framework not in _adapters:
        available = ", ".join(sorted(_adapters))
        msg = f"Unknown framework '{framework}'. Available: {available}"
        raise KeyError(msg)
    return _adapters[framework]


def list_frameworks() -> list[AgentAdapter]:
    """Return all registered adapters."""
    _discover()
    return sorted(_adapters.values(), key=lambda a: a.name)


def framework_names() -> list[str]:
    """Return names of all registered frameworks."""
    return [a.name for a in list_frameworks()]

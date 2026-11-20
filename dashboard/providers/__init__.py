from .base import GenRequest, Provider, ProviderError
from .custom import load_custom
from .hf_spaces import BUILTIN_HF
from .reel import ReelProvider


def all_providers() -> dict[str, Provider]:
    """Built-in + auto-connected providers (reloaded each call)."""
    items: list[Provider] = [ReelProvider(), *BUILTIN_HF, *load_custom()]
    return {p.id: p for p in items}


__all__ = ["GenRequest", "Provider", "ProviderError", "all_providers"]

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator

from app.core.config import get_settings
from app.providers.mock_provider import MockProvider
from app.providers.real_provider import RealMarketProvider

_provider_mode_override: ContextVar[str | None] = ContextVar("provider_mode_override", default=None)


class ProviderFactory:
    @staticmethod
    def create(mode: str | None = None):
        settings = get_settings()
        provider_mode = mode or _provider_mode_override.get() or settings.data_provider_mode
        if provider_mode == "mock":
            return MockProvider()
        if provider_mode in {"real", "cls"}:
            return RealMarketProvider()
        raise ValueError(f"Unsupported provider mode: {provider_mode}")

    @staticmethod
    @contextmanager
    def use_mode(mode: str | None) -> Iterator[None]:
        token = None
        if mode:
            token = _provider_mode_override.set(mode)
        try:
            yield
        finally:
            if token is not None:
                _provider_mode_override.reset(token)

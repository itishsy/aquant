from app.core.config import get_settings
from app.providers.mock_provider import MockProvider
from app.providers.real_provider import RealMarketProvider


class ProviderFactory:
    @staticmethod
    def create():
        settings = get_settings()
        if settings.data_provider_mode == "mock":
            return MockProvider()
        if settings.data_provider_mode in {"real", "cls"}:
            return RealMarketProvider()
        raise ValueError(f"Unsupported provider mode: {settings.data_provider_mode}")

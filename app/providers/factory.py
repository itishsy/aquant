from app.core.config import get_settings
from app.providers.mock_provider import MockProvider


class ProviderFactory:
    @staticmethod
    def create():
        settings = get_settings()
        if settings.data_provider_mode == "mock":
            return MockProvider()
        raise ValueError(f"Unsupported provider mode: {settings.data_provider_mode}")

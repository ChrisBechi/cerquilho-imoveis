from app.providers.base_provider import BaseProvider


def test_base_provider_has_name():
    assert hasattr(BaseProvider, "NAME")
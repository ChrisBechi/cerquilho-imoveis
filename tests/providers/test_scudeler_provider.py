import pytest
import requests

from app.providers.scudeler_provider import ScudelerProvider


def photos(count):
    return [{"Foto_Media": f"https://images.example/{index}.jpg"}
            for index in range(count)]


def sample_item():
    return {"ID": 2317, "Codigo": "2317", "Idimob": 1,
            "Nome": "CASA COM 2 DORMITORIOS", "AreaTotal": "0,00",
            "Tipo": [{"Valor": "1.450,00", "Dormitorios": 2}],
            "URL": "https://www.imobiliariascudeler.com.br/imovel/casa/2317",
            "Fotos": photos(5)}


def install_detail(monkeypatch, provider, detail):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": detail}

    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(provider.session, "get", get)
    return calls


def test_detail_gallery_includes_all_thirteen_photos(monkeypatch):
    provider = ScudelerProvider()
    calls = install_detail(monkeypatch, provider,
                           {"ID": 2317, "Fotos": {"Apresentacao": photos(13)}})

    listing = provider.parse_listing(sample_item(), "5515999999999")
    payload = provider.build_listing_payload(listing)

    assert len(listing.image_urls) == 13
    assert len(payload["image_urls"]) == 13
    assert listing.image_urls_complete
    assert listing.thumbnail_url == listing.image_urls[0]
    assert calls[0][0].endswith("/api/imovel/2317")
    assert calls[0][1]["params"] == {"rede": 0, "idimob": 1}


def test_images_preserve_order_deduplicate_and_support_size_fallbacks():
    urls = ScudelerProvider.extract_image_urls({
        "Apresentacao": [*photos(2), *photos(1), {"Foto_Grande": "https://images.example/large.jpg"}],
        "Plantas": [{"Foto_Pequena": "https://images.example/plan.jpg"}, None],
    })
    assert urls == ["https://images.example/0.jpg", "https://images.example/1.jpg",
                    "https://images.example/large.jpg", "https://images.example/plan.jpg"]


def test_failed_details_preserve_existing_gallery_and_keep_listing_metadata(monkeypatch):
    provider = ScudelerProvider()

    def fail(*_args, **_kwargs):
        raise requests.Timeout("Temporary failure")

    monkeypatch.setattr(provider.session, "get", fail)
    listing = provider.parse_listing(sample_item(), "5515999999999")
    payload = provider.build_listing_payload(listing)

    assert len(listing.image_urls) == 5
    assert not listing.image_urls_complete
    assert payload["image_urls"] == []
    assert payload["thumbnail_url"] == "https://images.example/0.jpg"
    assert payload["code"] == "2317"
    assert payload["current_price"] == 145000


@pytest.mark.parametrize("detail", [None, {}, {"ID": 2317, "Fotos": {}},
                                    {"ID": 999, "Fotos": {"Apresentacao": photos(13)}}])
def test_incomplete_or_wrong_detail_cannot_replace_gallery(monkeypatch, detail):
    provider = ScudelerProvider()
    install_detail(monkeypatch, provider, detail)
    assert provider.fetch_listing_images(2317) is None


def test_flat_photo_list_remains_supported():
    assert len(ScudelerProvider.extract_image_urls(photos(13))) == 13

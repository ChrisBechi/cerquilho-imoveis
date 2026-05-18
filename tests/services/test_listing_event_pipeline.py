from copy import deepcopy
from datetime import datetime, timedelta, timezone

import app.services.listing_service as listing_service_module
from app.services.listing_service import ListingsService


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "listings": [],
            "listing_events": [],
            "listing_price_history": [],
            "listing_images": [],
            "provider_execution_log": [],
        }
        self.next_ids = {
            table: 1
            for table in self.tables
        }

    def table(self, name):
        return FakeQuery(self, name)

    def insert_row(self, table, payload):
        row = deepcopy(payload)
        row.setdefault("id", self.next_ids[table])
        self.next_ids[table] += 1
        row.setdefault(
            "created_at",
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        self.tables[table].append(row)
        return row


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.filters = []
        self.payload = None
        self.operation = "select"
        self.limit_value = None
        self.order_field = None
        self.order_desc = False

    def select(self, *_args):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, field, value):
        self.filters.append(lambda row: row.get(field) == value)
        return self

    def match(self, values):
        for field, value in values.items():
            self.eq(field, value)
        return self

    def is_(self, field, value):
        self.filters.append(lambda row: row.get(field) is value)
        return self

    def lt(self, field, value):
        self.filters.append(lambda row: row.get(field) is not None and row.get(field) < value)
        return self

    def in_(self, field, values):
        allowed = set(values)
        self.filters.append(lambda row: row.get(field) in allowed)
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        rows = self.client.tables[self.table_name]

        if self.operation == "insert":
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            inserted = [
                self.client.insert_row(self.table_name, payload)
                for payload in payloads
            ]
            return FakeResponse(deepcopy(inserted))

        matched = [
            row
            for row in rows
            if all(filter_fn(row) for filter_fn in self.filters)
        ]

        if self.order_field:
            matched = sorted(
                matched,
                key=lambda row: row.get(self.order_field) or "",
                reverse=self.order_desc,
            )

        if self.limit_value is not None:
            matched = matched[:self.limit_value]

        if self.operation == "update":
            for row in matched:
                row.update(deepcopy(self.payload))
            return FakeResponse(deepcopy(matched))

        if self.operation == "delete":
            self.client.tables[self.table_name] = [
                row
                for row in rows
                if row not in matched
            ]
            return FakeResponse(deepcopy(matched))

        return FakeResponse(deepcopy(matched))


def sample_payload(price=245000, price_label="R$ 2.450 (aluguel)"):
    return {
        "provider": "Provider Teste",
        "code": "ABC123",
        "title": "Casa residencial no centro",
        "neighborhood": "Centro",
        "bedrooms": 2,
        "bathrooms": 1,
        "area": 70,
        "url": "https://example.com/imovel/abc123",
        "thumbnail_url": "https://example.com/image.jpg",
        "current_price": price,
        "price_label": price_label,
        "image_urls": [],
    }


def install_fake_supabase(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(listing_service_module, "supabase", fake)
    return fake


def event_types(fake):
    return [
        event["type"]
        for event in fake.tables["listing_events"]
    ]


def test_new_listing_creates_created_event_once(monkeypatch):
    fake = install_fake_supabase(monkeypatch)

    ListingsService.upsert_listing(sample_payload())
    ListingsService.upsert_listing(sample_payload())

    assert event_types(fake) == ["created"]
    assert fake.tables["listings"][0]["current_price"] == 245000
    assert fake.tables["listings"][0]["last_seen_at"] is not None


def test_price_drop_creates_event_with_history_and_labels(monkeypatch):
    fake = install_fake_supabase(monkeypatch)

    ListingsService.upsert_listing(sample_payload(price=245000, price_label="R$ 2.450"))
    ListingsService.upsert_listing(sample_payload(price=220000, price_label="R$ 2.200"))

    event = fake.tables["listing_events"][-1]
    assert event["type"] == "price_drop"
    assert event["old_price"] == 245000
    assert event["new_price"] == 220000
    assert event["old_price_label"] == "R$ 2.450"
    assert event["new_price_label"] == "R$ 2.200"
    assert [row["price"] for row in fake.tables["listing_price_history"]] == [220000]


def test_price_up_creates_event(monkeypatch):
    fake = install_fake_supabase(monkeypatch)

    ListingsService.upsert_listing(sample_payload(price=220000))
    ListingsService.upsert_listing(sample_payload(price=245000))

    event = fake.tables["listing_events"][-1]
    assert event["type"] == "price_up"
    assert event["old_price"] == 220000
    assert event["new_price"] == 245000


def test_invalid_temporary_price_does_not_create_false_drop(monkeypatch):
    fake = install_fake_supabase(monkeypatch)

    ListingsService.upsert_listing(sample_payload(price=245000))
    ListingsService.upsert_listing(sample_payload(price=0, price_label=""))

    assert event_types(fake) == ["created"]
    assert fake.tables["listings"][0]["current_price"] == 245000
    assert fake.tables["listing_price_history"] == []


def test_listing_missing_this_run_is_marked_rented_immediately(monkeypatch):
    fake = install_fake_supabase(monkeypatch)
    ListingsService.upsert_listing({
        **sample_payload(),
        "image_urls": [
            "https://example.com/old-1.jpg",
            "https://example.com/old-2.jpg",
        ],
    })
    fake.tables["listings"][0]["last_seen_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=23)
    ).replace(microsecond=0).isoformat()
    run_started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    rented = ListingsService.detect_rented_listings(
        ["Provider Teste"],
        run_started_at=run_started_at,
    )

    assert len(rented) == 1
    assert fake.tables["listings"][0]["is_active"] is False
    assert fake.tables["listings"][0]["rented_at"] is not None
    assert fake.tables["listings"][0]["thumbnail_url"] == ListingsService.rented_image_url()
    assert len(fake.tables["listing_images"]) == 1
    assert fake.tables["listing_images"][0]["listing_id"] == 1
    assert fake.tables["listing_images"][0]["image_url"] == ListingsService.rented_image_url()
    assert "rented" in event_types(fake)


def test_listing_missing_for_more_than_24h_is_marked_rented_once(monkeypatch):
    fake = install_fake_supabase(monkeypatch)
    ListingsService.upsert_listing(sample_payload())
    fake.tables["listings"][0]["last_seen_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=25)
    ).replace(microsecond=0).isoformat()

    run_started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    first = ListingsService.detect_rented_listings(
        ["Provider Teste"],
        run_started_at=run_started_at,
    )
    second = ListingsService.detect_rented_listings(
        ["Provider Teste"],
        run_started_at=run_started_at,
    )

    assert len(first) == 1
    assert second == []
    assert fake.tables["listings"][0]["is_active"] is False
    assert fake.tables["listings"][0]["rented_at"] is not None
    assert event_types(fake).count("rented") == 1


def test_provider_failure_does_not_generate_mass_rented(monkeypatch):
    fake = install_fake_supabase(monkeypatch)
    ListingsService.upsert_listing(sample_payload())
    fake.tables["listings"][0]["last_seen_at"] = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).replace(microsecond=0).isoformat()

    run_started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    rented = ListingsService.detect_rented_listings(
        [],
        run_started_at=run_started_at,
    )

    assert rented == []
    assert fake.tables["listings"][0]["rented_at"] is None
    assert "rented" not in event_types(fake)

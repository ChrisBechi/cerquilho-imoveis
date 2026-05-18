import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from app.config.event_config import (
    BugProtection,
    EventMessages,
    ListingEventType,
    RentedDetectionConfig,
)
from app.config.supabase import supabase


class ListingsService:
    """
    Persistence and event pipeline for scraped listings.

    Providers should only report what they saw. This service decides what changed,
    writes consistent listing state, and emits the official frontend event types.
    """

    @staticmethod
    def rented_image_url() -> str:
        configured_url = os.getenv("RENTED_IMAGE_URL")

        if configured_url:
            return configured_url

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 800'>"
            "<rect width='1200' height='800' fill='#1f2937'/>"
            "<rect x='80' y='80' width='1040' height='640' rx='28' fill='#f8fafc'/>"
            "<rect x='80' y='322' width='1040' height='156' fill='#dc2626'/>"
            "<text x='600' y='425' text-anchor='middle' "
            "font-family='Arial,sans-serif' font-size='118' "
            "font-weight='700' fill='white'>ALUGADO</text>"
            "<text x='600' y='560' text-anchor='middle' "
            "font-family='Arial,sans-serif' font-size='44' "
            "font-weight='500' fill='#374151'>Imovel indisponivel</text>"
            "</svg>"
        )

        return f"data:image/svg+xml,{quote(svg, safe='')}"

    @staticmethod
    def now_timestamp() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def rented_cutoff_timestamp(
        hours_before_rented: int | None = None,
    ) -> str:
        hours = (
            hours_before_rented
            if hours_before_rented is not None
            else ListingsService.rented_detection_hours()
        )
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return cutoff.replace(microsecond=0).isoformat()

    @staticmethod
    def rented_detection_hours() -> int:
        raw_value = os.getenv("RENTED_DETECTION_HOURS")

        if raw_value:
            try:
                hours = int(raw_value)
                if hours > 0:
                    return hours
            except ValueError:
                print(
                    f"[RENTED CONFIG WARNING] invalid RENTED_DETECTION_HOURS={raw_value}"
                )

        return RentedDetectionConfig.HOURS_BEFORE_RENTED

    @staticmethod
    def normalize_price(value: Any) -> int:
        try:
            price = int(value or 0)
        except (TypeError, ValueError):
            return 0

        if price < 0:
            return 0

        return price

    @staticmethod
    def is_valid_title(title: str) -> bool:
        return (
            isinstance(title, str)
            and len(title.strip()) >= BugProtection.MIN_TITLE_LENGTH
        )

    @staticmethod
    def is_valid_price(price: int) -> bool:
        return BugProtection.MIN_PRICE <= price <= BugProtection.MAX_PRICE

    @staticmethod
    def has_duplicate_event(
        listing_id: int,
        event_type: str,
        old_price: int | None = None,
        new_price: int | None = None,
    ) -> bool:
        response = (
            supabase
            .table("listing_events")
            .select("id,type,old_price,new_price")
            .eq("listing_id", listing_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return False

        latest = response.data[0]
        return (
            latest.get("type") == event_type
            and latest.get("old_price") == old_price
            and latest.get("new_price") == new_price
        )

    @staticmethod
    def create_event(
        listing_id: int,
        event_type: str,
        title: str,
        description: str,
        old_price: int | None = None,
        new_price: int | None = None,
        old_price_label: str | None = None,
        new_price_label: str | None = None,
    ) -> bool:
        official_types = {item.value for item in ListingEventType}
        if event_type not in official_types:
            raise ValueError(f"Invalid listing event type: {event_type}")

        if ListingsService.has_duplicate_event(
            listing_id,
            event_type,
            old_price,
            new_price,
        ):
            print(
                f"[EVENT SKIPPED] duplicate listing_id={listing_id} "
                f"type={event_type} old_price={old_price} new_price={new_price}"
            )
            return False

        event_payload = {
            "listing_id": listing_id,
            "type": event_type,
            "title": title,
            "description": description,
            "old_price": int(old_price) if old_price is not None else None,
            "new_price": int(new_price) if new_price is not None else None,
            "old_price_label": old_price_label,
            "new_price_label": new_price_label,
        }

        (
            supabase
            .table("listing_events")
            .insert(event_payload)
            .execute()
        )

        print(
            f"[EVENT CREATED] listing_id={listing_id} "
            f"type={event_type} old_price={old_price} new_price={new_price}"
        )
        return True

    @staticmethod
    def sync_images(
        listing_id: int,
        image_urls: list[str],
    ):
        if not image_urls:
            return

        existing = (
            supabase
            .table("listing_images")
            .select("image_url")
            .eq("listing_id", listing_id)
            .execute()
        )

        existing_urls = {
            item["image_url"]
            for item in existing.data
        }

        new_images = [
            {
                "listing_id": listing_id,
                "image_url": image_url,
            }
            for image_url in image_urls[:BugProtection.MAX_IMAGES]
            if image_url not in existing_urls
        ]

        if new_images:
            (
                supabase
                .table("listing_images")
                .insert(new_images)
                .execute()
            )

            print(f"{len(new_images)} imagens adicionadas")

    @staticmethod
    def replace_with_rented_image(
        listing_id: int,
    ):
        image_url = ListingsService.rented_image_url()

        (
            supabase
            .table("listing_images")
            .delete()
            .eq("listing_id", listing_id)
            .execute()
        )

        (
            supabase
            .table("listing_images")
            .insert({
                "listing_id": listing_id,
                "image_url": image_url,
            })
            .execute()
        )

        print(
            f"[RENTED IMAGE UPDATED] listing_id={listing_id} "
            "gallery_replaced=true"
        )

    @staticmethod
    def insert_price_history_if_changed(
        listing_id: int,
        new_price: int,
    ) -> bool:
        latest = (
            supabase
            .table("listing_price_history")
            .select("price")
            .eq("listing_id", listing_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if latest.data and ListingsService.normalize_price(
            latest.data[0].get("price")
        ) == new_price:
            print(
                f"[PRICE HISTORY SKIPPED] listing_id={listing_id} "
                f"price={new_price}"
            )
            return False

        (
            supabase
            .table("listing_price_history")
            .insert({
                "listing_id": listing_id,
                "price": int(new_price),
            })
            .execute()
        )
        return True

    @staticmethod
    def build_listing_update_payload(
        payload: dict,
        current_price: int,
        timestamp: str,
    ) -> dict:
        return {
            "provider": payload["provider"],
            "code": payload.get("code"),
            "title": payload["title"],
            "neighborhood": payload["neighborhood"],
            "bedrooms": int(payload["bedrooms"] or 0),
            "bathrooms": int(payload["bathrooms"] or 0),
            "area": int(payload["area"] or 0),
            "url": payload["url"],
            "thumbnail_url": payload["thumbnail_url"],
            "current_price": int(current_price),
            "price_label": payload["price_label"],
            "last_seen_at": timestamp,
            "updated_at": timestamp,
            "is_active": True,
            "rented_at": None,
            "provider_last_status": "success",
            "provider_last_execution": timestamp,
        }

    @staticmethod
    def upsert_listing(payload: dict):
        timestamp = ListingsService.now_timestamp()
        incoming_price = ListingsService.normalize_price(
            payload.get("current_price")
        )

        if not ListingsService.is_valid_title(payload.get("title", "")):
            print(
                f"[LISTING SKIPPED] invalid title provider={payload.get('provider')} "
                f"code={payload.get('code')}"
            )
            return []

        print(
            f"[LISTING SEEN] provider={payload.get('provider')} "
            f"code={payload.get('code')} current_price={incoming_price} "
            f"price_label='{payload.get('price_label')}'"
        )

        if payload.get("code"):
            existing = (
                supabase
                .table("listings")
                .select("*")
                .match({
                    "provider": payload["provider"],
                    "code": payload["code"],
                })
                .limit(1)
                .execute()
            )
        else:
            existing = (
                supabase
                .table("listings")
                .select("*")
                .eq("url", payload["url"])
                .limit(1)
                .execute()
            )

        if existing.data:
            listing = existing.data[0]
            listing_id = listing["id"]
            old_price = ListingsService.normalize_price(
                listing.get("current_price")
            )
            new_price = incoming_price
            old_price_label = listing.get("price_label")
            new_price_label = payload.get("price_label")

            if (
                ListingsService.is_valid_price(old_price)
                and not ListingsService.is_valid_price(new_price)
            ):
                print(
                    f"[PRICE IGNORED] invalid incoming price listing_id={listing_id} "
                    f"provider={payload.get('provider')} code={payload.get('code')} "
                    f"old_price={old_price} incoming_price={new_price}"
                )
                new_price = old_price

            print(
                f"[LISTING UPDATE] listing_id={listing_id} "
                f"provider={payload.get('provider')} code={payload.get('code')} "
                f"old_price={old_price} new_price={new_price}"
            )

            response = (
                supabase
                .table("listings")
                .update(
                    ListingsService.build_listing_update_payload(
                        payload,
                        new_price,
                        timestamp,
                    )
                )
                .eq("id", listing_id)
                .execute()
            )

            price_changed = old_price != new_price
            valid_new_price = ListingsService.is_valid_price(new_price)
            valid_price_event = (
                price_changed
                and ListingsService.is_valid_price(old_price)
                and valid_new_price
            )

            if price_changed and valid_new_price:
                ListingsService.insert_price_history_if_changed(
                    listing_id,
                    new_price,
                )

            if valid_price_event:
                event_type = (
                    ListingEventType.PRICE_DROP.value
                    if new_price < old_price
                    else ListingEventType.PRICE_UP.value
                )
                message = (
                    EventMessages.PRICE_DROP
                    if new_price < old_price
                    else EventMessages.PRICE_UP
                )

                print(
                    f"[PRICE CHANGED] listing_id={listing_id} "
                    f"provider={payload.get('provider')} code={payload.get('code')} "
                    f"old_price={old_price} new_price={new_price} "
                    f"old_price_label='{old_price_label}' "
                    f"new_price_label='{new_price_label}'"
                )

                ListingsService.create_event(
                    listing_id=listing_id,
                    event_type=event_type,
                    title=message["title"],
                    description=payload["title"],
                    old_price=old_price,
                    new_price=new_price,
                    old_price_label=old_price_label,
                    new_price_label=new_price_label,
                )

            ListingsService.sync_images(
                listing_id,
                payload.get("image_urls", []),
            )

            print("LISTING UPDATED")
            return response.data

        new_price = incoming_price

        insert_payload = ListingsService.build_listing_update_payload(
            payload,
            new_price,
            timestamp,
        )

        response = (
            supabase
            .table("listings")
            .insert(insert_payload)
            .execute()
        )

        created_listing = response.data[0]
        listing_id = created_listing["id"]

        ListingsService.create_event(
            listing_id=listing_id,
            event_type=ListingEventType.CREATED.value,
            title=EventMessages.CREATED["title"],
            description=payload["title"],
        )

        ListingsService.sync_images(
            listing_id,
            payload.get("image_urls", []),
        )

        print(f"LISTING CREATED id={listing_id}")
        return response.data

    @staticmethod
    def mark_provider_execution(
        provider_name: str,
        status: str,
        listings_found: int = 0,
        error_message: str | None = None,
    ):
        timestamp = ListingsService.now_timestamp()

        print(
            f"[PROVIDER STATUS] provider={provider_name} status={status} "
            f"listings_found={listings_found} error={error_message}"
        )

        payload = {
            "provider_last_status": status,
            "provider_last_execution": timestamp,
        }

        (
            supabase
            .table("listings")
            .update(payload)
            .eq("provider", provider_name)
            .execute()
        )

        log_payload = {
            "provider_name": provider_name,
            "execution_end": timestamp,
            "status": status,
            "listings_found": int(listings_found or 0),
            "error_message": error_message,
        }

        try:
            (
                supabase
                .table("provider_execution_log")
                .insert(log_payload)
                .execute()
            )
        except Exception as error:
            print(
                f"[PROVIDER LOG SKIPPED] provider={provider_name} "
                f"error={error}"
            )

    @staticmethod
    def detect_rented_listings(
        successful_providers: list[str],
        hours_before_rented: int | None = None,
        run_started_at: str | None = None,
    ) -> list[dict]:
        providers = sorted({
            provider
            for provider in successful_providers
            if provider
        })

        if not providers:
            print(
                "[RENTED DETECTION SKIPPED] no successful providers; "
                "protecting against provider failure or timeout"
            )
            return []

        if run_started_at:
            print(
                f"[RENTED DETECTION] providers={providers} "
                f"mode=absolute_missing_this_run run_started_at={run_started_at}"
            )

            candidates = (
                supabase
                .table("listings")
                .select("*")
                .in_("provider", providers)
                .eq("is_active", True)
                .is_("rented_at", None)
                .lt("last_seen_at", run_started_at)
                .execute()
            )
        else:
            cutoff = ListingsService.rented_cutoff_timestamp(
                hours_before_rented
            )

            print(
                f"[RENTED DETECTION] providers={providers} "
                f"mode=cutoff_fallback cutoff={cutoff} "
                f"hours={hours_before_rented or ListingsService.rented_detection_hours()}"
            )

            candidates = (
                supabase
                .table("listings")
                .select("*")
                .in_("provider", providers)
                .eq("is_active", True)
                .is_("rented_at", None)
                .lt("last_seen_at", cutoff)
                .execute()
            )

        rented_listings = []
        timestamp = ListingsService.now_timestamp()

        for listing in candidates.data:
            listing_id = listing["id"]

            if listing.get("rented_at") is not None:
                print(
                    f"[RENTED SKIPPED] already rented listing_id={listing_id}"
                )
                continue

            provider = listing.get("provider")
            code = listing.get("code")

            print(
                f"[RENTED DETECTED] listing_id={listing_id} provider={provider} "
                f"code={code} last_seen_at={listing.get('last_seen_at')} "
                f"run_started_at={run_started_at}"
            )

            update_response = (
                supabase
                .table("listings")
                .update({
                    "is_active": False,
                    "rented_at": timestamp,
                    "thumbnail_url": ListingsService.rented_image_url(),
                    "updated_at": timestamp,
                })
                .eq("id", listing_id)
                .is_("rented_at", None)
                .execute()
            )

            if not update_response.data:
                print(
                    f"[RENTED SKIPPED] stale candidate listing_id={listing_id} "
                    "was already changed"
                )
                continue

            ListingsService.replace_with_rented_image(
                listing_id
            )

            event_created = ListingsService.create_event(
                listing_id=listing_id,
                event_type=ListingEventType.RENTED.value,
                title=EventMessages.RENTED["title"],
                description=listing.get("title") or EventMessages.RENTED["description"],
            )

            if event_created:
                rented_listings.append(listing)

        print(
            f"[RENTED DETECTION DONE] candidates={len(candidates.data)} "
            f"events={len(rented_listings)}"
        )

        return rented_listings

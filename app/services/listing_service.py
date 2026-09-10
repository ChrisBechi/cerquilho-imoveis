import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import requests

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
    def is_missing_schema_column_error(
        error: Exception,
    ) -> bool:
        return (
            "PGRST204" in str(error)
            or "schema cache" in str(error)
            or "Could not find the" in str(error)
        )

    @staticmethod
    def execute_with_schema_fallback(
        query_builder,
        payload: dict,
        fallback_payload: dict,
        context: str,
    ):
        try:
            return query_builder(payload).execute()
        except Exception as error:
            if not ListingsService.is_missing_schema_column_error(error):
                raise

            print(
                f"[SCHEMA FALLBACK] context={context} error={error} "
                "retrying without optional columns"
            )
            return query_builder(fallback_payload).execute()

    @staticmethod
    def ensure_mutation_applied(response, context: str):
        if not getattr(response, "data", None):
            raise PermissionError(
                f"Supabase não alterou nenhuma linha em {context}. "
                "Verifique se SUPABASE_KEY contém a chave service_role "
                "e se o registro está acessível pelas políticas RLS."
            )

        return response

    @staticmethod
    def rented_image_url() -> str:
        return (
            os.getenv("RENTED_IMAGE_URL")
            or "https://i.imgur.com/qK0Bms2.png?w=800&q=80"
        )

    @staticmethod
    def image_bucket_name() -> str:
        return os.getenv("SUPABASE_IMAGE_BUCKET", "cerq-imoveis")

    @staticmethod
    def image_storage_path(listing_id: int, image_url: str) -> str:
        digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:24]
        extension = os.path.splitext(urlparse(image_url).path)[1].lower()

        if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
            extension = ".jpg"

        return f"listings/{listing_id}/{digest}{extension}"

    @staticmethod
    def stored_image_url(listing_id: int, image_url: str) -> str:
        bucket_name = ListingsService.image_bucket_name()
        public_prefix = f"/storage/v1/object/public/{bucket_name}/"

        if public_prefix in image_url:
            return image_url

        storage_path = ListingsService.image_storage_path(
            listing_id,
            image_url,
        )
        bucket = supabase.storage.from_(bucket_name)
        return bucket.get_public_url(storage_path)

    @staticmethod
    def store_image(listing_id: int, image_url: str) -> str:
        bucket_name = ListingsService.image_bucket_name()
        public_prefix = f"/storage/v1/object/public/{bucket_name}/"

        if public_prefix in image_url:
            return image_url

        storage_path = ListingsService.image_storage_path(
            listing_id,
            image_url,
        )
        public_url = ListingsService.stored_image_url(listing_id, image_url)
        bucket = supabase.storage.from_(bucket_name)

        response = requests.get(
            image_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/136.0 Safari/537.36"
                )
            },
            timeout=30,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not content_type.startswith("image/"):
            raise ValueError(f"URL não retornou uma imagem: {image_url}")

        max_image_bytes = 15 * 1024 * 1024
        if len(response.content) > max_image_bytes:
            raise ValueError(f"Imagem excede 15 MB: {image_url}")

        bucket.upload(
            path=storage_path,
            file=response.content,
            file_options={
                "content-type": content_type,
                "cache-control": "31536000",
                "upsert": "true",
            },
        )

        return public_url

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
    ) -> int:
        if not image_urls:
            print(
                f"[IMAGE SYNC] listing_id={listing_id} "
                "found=0 existing=0 added=0"
            )
            return 0

        source_urls = list(dict.fromkeys(
            image_url.strip()
            for image_url in image_urls
            if image_url and image_url.strip()
        ))[:BugProtection.MAX_IMAGES]

        try:
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

            stored_urls = []

            for source_url in source_urls:
                try:
                    expected_url = ListingsService.stored_image_url(
                        listing_id,
                        source_url,
                    )
                    if expected_url in existing_urls:
                        stored_urls.append(expected_url)
                        continue

                    stored_url = ListingsService.store_image(
                        listing_id,
                        source_url,
                    )
                    if stored_url not in stored_urls:
                        stored_urls.append(stored_url)
                except Exception as error:
                    print(
                        f"[IMAGE UPLOAD FAILED] listing_id={listing_id} "
                        f"url={source_url} error={error}"
                    )

            new_images = [
                {"listing_id": listing_id, "image_url": stored_url}
                for stored_url in stored_urls
                if stored_url not in existing_urls
            ]

            # The provider gallery is authoritative. Keeping URLs that have
            # disappeared from it can leave an old "alugado" banner attached
            # to a listing that became active again.
            obsolete_urls = (
                existing_urls - set(stored_urls)
                if len(stored_urls) == len(source_urls)
                else set()
            )

            for obsolete_url in obsolete_urls:
                (
                    supabase
                    .table("listing_images")
                    .delete()
                    .eq("listing_id", listing_id)
                    .eq("image_url", obsolete_url)
                    .execute()
                )

            if new_images:
                (
                    supabase
                    .table("listing_images")
                    .insert(new_images)
                    .execute()
                )

            print(
                f"[IMAGE SYNC] listing_id={listing_id} "
                f"found={len(source_urls)} stored={len(stored_urls)} "
                f"existing={len(existing_urls)} "
                f"added={len(new_images)} removed={len(obsolete_urls)}"
            )

            return len(new_images)

        except Exception as error:
            # Image synchronization is retried the next time the listing is seen.
            # It must not make a valid listing disappear from the provider run.
            print(
                f"[IMAGE SYNC FAILED] listing_id={listing_id} "
                f"found={len(source_urls)} error={error}"
            )

            return 0

    @staticmethod
    def sync_thumbnail(listing_id: int, thumbnail_url: str) -> str:
        if not thumbnail_url:
            return ""

        try:
            stored_url = ListingsService.store_image(
                listing_id,
                thumbnail_url,
            )
            (
                supabase
                .table("listings")
                .update({"thumbnail_url": stored_url})
                .eq("id", listing_id)
                .execute()
            )
            return stored_url
        except Exception as error:
            print(
                f"[THUMBNAIL UPLOAD FAILED] listing_id={listing_id} "
                f"url={thumbnail_url} error={error}"
            )
            return ""

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
            include_optional_columns: bool = True,
    ) -> dict:

        listing_payload = {
            "provider": payload["provider"],
            "contact": payload.get("contact", ""),
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
            "updated_at": timestamp,
        }

        if not include_optional_columns:
            return listing_payload

        listing_payload.update({
            "last_seen_at": timestamp,
            "is_active": True,
            "rented_at": None,
            "provider_last_status": "success",
            "provider_last_execution": timestamp,
        })

        return listing_payload

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

            response = ListingsService.execute_with_schema_fallback(
                query_builder=lambda update_payload: (
                    supabase
                    .table("listings")
                    .update(update_payload)
                    .eq("id", listing_id)
                ),
                payload=ListingsService.build_listing_update_payload(
                    payload,
                    new_price,
                    timestamp,
                ),
                fallback_payload=ListingsService.build_listing_update_payload(
                    payload,
                    new_price,
                    timestamp,
                    include_optional_columns=False,
                ),
                context="listing_update",
            )
            ListingsService.ensure_mutation_applied(
                response,
                f"listing_update listing_id={listing_id}",
            )

            changed_fields = [
                field
                for field in (
                    "contact",
                    "title",
                    "neighborhood",
                    "bedrooms",
                    "bathrooms",
                    "area",
                    "url",
                    "thumbnail_url",
                    "price_label",
                )
                if listing.get(field) != payload.get(field)
            ]
            if old_price != new_price:
                changed_fields.append("current_price")

            print(
                f"[LISTING FIELDS UPDATED] listing_id={listing_id} "
                f"fields={','.join(changed_fields) or 'timestamps'}"
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
            ListingsService.sync_thumbnail(
                listing_id,
                payload.get("thumbnail_url", ""),
            )

            print("LISTING UPDATED")
            return response.data

        new_price = incoming_price

        insert_payload = ListingsService.build_listing_update_payload(
            payload,
            new_price,
            timestamp,
        )

        response = ListingsService.execute_with_schema_fallback(
            query_builder=lambda insert_payload: (
                supabase
                .table("listings")
                .insert(insert_payload)
            ),
            payload=insert_payload,
            fallback_payload=ListingsService.build_listing_update_payload(
                payload,
                new_price,
                timestamp,
                include_optional_columns=False,
            ),
            context="listing_insert",
        )
        ListingsService.ensure_mutation_applied(
            response,
            "listing_insert",
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
        ListingsService.sync_thumbnail(
            listing_id,
            payload.get("thumbnail_url", ""),
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

        try:
            (
                supabase
                .table("listings")
                .update(payload)
                .eq("provider", provider_name)
                .execute()
            )
        except Exception as error:
            if not ListingsService.is_missing_schema_column_error(error):
                raise

            print(
                f"[PROVIDER STATUS SKIPPED] provider={provider_name} "
                f"schema_missing_optional_columns error={error}"
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

            rented_payload = {
                "is_active": False,
                "rented_at": timestamp,
                "thumbnail_url": ListingsService.rented_image_url(),
                "updated_at": timestamp,
            }

            rented_fallback_payload = {
                "thumbnail_url": ListingsService.rented_image_url(),
                "updated_at": timestamp,
            }

            update_response = ListingsService.execute_with_schema_fallback(
                query_builder=lambda update_payload: (
                    supabase
                    .table("listings")
                    .update(update_payload)
                    .eq("id", listing_id)
                    .is_("rented_at", None)
                ),
                payload=rented_payload,
                fallback_payload=rented_fallback_payload,
                context="rented_update",
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

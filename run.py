import platform

from app.providers.dr_adinho_provider import (
    DrAdinhoProvider
)

from app.providers.elizandra_soares_provider import (
    ElizandraProvider
)

from app.providers.rr_provider import (
    RRProvider
)

from app.providers.scudeler_provider import (
    ScudelerProvider
)

from app.providers.terrazzo_provider import (
    TerrazzoProvider
)

from app.services.Telegram.telegram_notifier import (
    TelegramNotifier
)

from app.services.Windows.windows_notifier import (
    WindowsNotifier
)

from app.services.email_notifier import (
    EmailNotifier
)

from app.services.event_notifications_service import (
    EventNotificationsService
)

from app.services.listing_payload_builder import (
    ListingPayloadBuilder
)

from app.services.listing_service import (
    ListingsService
)

from app.services.whatsapp.whatsapp_notifier import (
    WhatsAppNotifier
)


def main():

    run_started_at = ListingsService.now_timestamp()

    providers = [
        # TerrazzoProvider(),
        # DrAdinhoProvider(),
        # RRProvider(),
        ScudelerProvider(),
        ElizandraProvider()
    ]

    # ==========================================
    # EXECUTA PROVIDERS
    # ==========================================

    successful_providers = []

    for provider in providers:
        try:

            print(
                f"Executando provider: {provider.NAME}"
            )

            listings = provider.fetch_listings()
            listings_found = len(listings or [])

            if listings_found > 0:
                successful_providers.append(provider.NAME)
                ListingsService.mark_provider_execution(
                    provider.NAME,
                    "success",
                    listings_found,
                )
            else:
                print(
                    f"[PROVIDER EMPTY] provider={provider.NAME} "
                    "returned zero listings; rented detection disabled for it"
                )
                ListingsService.mark_provider_execution(
                    provider.NAME,
                    "partial",
                    listings_found,
                    "Provider returned zero listings",
                )

        except Exception as error:

            print(
                f"Erro provider {provider.NAME}: {error}"
            )

            ListingsService.mark_provider_execution(
                provider.NAME,
                "failed",
                0,
                str(error),
            )

    # ==========================================
    # RENTED DETECTION
    # ==========================================

    ListingsService.detect_rented_listings(
        successful_providers,
        run_started_at=run_started_at,
    )

    # ==========================================
    # EVENTOS PENDENTES
    # ==========================================

    pending_events = (

        EventNotificationsService

        .get_pending_events()
    )

    print(
        f"Eventos pendentes: {len(pending_events)}"
    )

    if not pending_events:

        print(
            "Nenhum evento pendente."
        )

        return

    # ==========================================
    # EMAIL BATCH
    # ==========================================

    new_listing_payloads = []
    price_change_payloads = []
    rented_payloads = []

    # ==========================================
    # PROCESSA EVENTOS
    # ==========================================

    for event in pending_events:

        try:

            listing = (

                ListingPayloadBuilder

                .build(
                    event["listing_id"]
                )
            )

            # ==================================
            # CREATED
            # ==================================

            if (
                event["type"]
                == "created"
            ):

                # ==============================
                # EMAIL BATCH
                # ==============================

                new_listing_payloads.append(
                    listing
                )

            # ==================================
            # PRICE CHANGE
            # ==================================

            elif (
                event["type"]
                in [
                    "price_drop",
                    "price_up"
                ]
            ):

                change_payload = {

                    "listing":
                        listing,

                    "old_price":
                        event["old_price"],

                    "new_price":
                        event["new_price"],

                    "is_lower":
                        event["new_price"]
                        < event["old_price"]
                }

                price_change_payloads.append(
                    change_payload
                )

            # ==================================
            # RENTED
            # ==================================

            elif (
                event["type"]
                == "rented"
            ):

                rented_payloads.append(
                    listing
                )

            # ==================================
            # MARCA COMO NOTIFICADO
            # ==================================

            EventNotificationsService.mark_as_notified(
                event["id"]
            )

        except Exception as error:

            print(
                f"Erro processando evento: {error}"
            )

    # ==========================================
    # ENVIA EMAIL ÚNICO
    # ==========================================

    if new_listing_payloads or price_change_payloads or rented_payloads:

        try:
            email = EmailNotifier()
            if new_listing_payloads:
                email.send_new_listings(
                    new_listing_payloads
                )

            if price_change_payloads:
                email.send_price_changes(
                    price_change_payloads
                )

        except Exception as error:

            print(
                f"Erro email: {error}"
            )

        if rented_payloads:
            print(
                f"Eventos rented pendentes para realtime: {len(rented_payloads)}"
            )

        try:
            whatsapp = WhatsAppNotifier()

            for listing in new_listing_payloads:
                whatsapp.send_new_listing(
                    listing
                )

            for item in price_change_payloads:
                whatsapp.send_price_change(
                    item
                )
        except Exception as e:
            print(e)


        try:
            telegram = TelegramNotifier()

            for listing in new_listing_payloads:
                telegram.send_new_listing(
                    listing
                )

            for item in price_change_payloads:
                telegram.send_price_change(
                    item
                )
        except Exception as e:
            print(e)

        if platform.system() == "Windows":

            try:
                windows = WindowsNotifier()

                for listing in new_listing_payloads:
                    windows.send_new_listing(
                        listing
                    )

                for item in price_change_payloads:
                    windows.send_price_change(
                        item
                    )

            except Exception as e:

                print(e)

    print(
        "Scraping finalizado"
    )


if __name__ == "__main__":
    main()

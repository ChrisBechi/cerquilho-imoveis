import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config.settings import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    EMAIL_TO
)
from app.utils.price_utils import format_price


class EmailNotifier:

    def send_new_listings(
        self,
        listings
    ):
        if not listings:

            print("Nenhum novo anÃºncio.")

            return

        grouped = {}

        def listing_value(
                listing,
                key,
                default=""
        ):

            if isinstance(
                listing,
                dict
            ):
                return listing.get(
                    key,
                    default
                )

            return getattr(
                listing,
                key,
                default
            )

        for listing in listings:

            provider = listing_value(
                listing,
                "provider"
            )

            if provider not in grouped:
                grouped[provider] = []

            grouped[provider].append(
                listing
            )

        html = """
        <h1 style="
            color:#111827;
            font-size:36px;
            line-height:1.2;
            margin-bottom:30px;
        ">
            &#128293; Novos im&oacute;veis encontrados
        </h1>
        """

        for provider, items in grouped.items():

            for listing in items:
                thumbnails_html = ""

                main_image = listing_value(
                    listing,
                    "thumbnail_url"
                )

                image_urls = (
                    listing_value(
                        listing,
                        "image_urls",
                        []
                    )
                    or []
                )

                if image_urls:

                    for image in image_urls[1:7]:
                        thumbnails_html += f"""
                        <img
                            src="{image}"
                            style="
                                width:90px;
                                height:70px;
                                object-fit:cover;
                                border-radius:8px;
                                margin-right:6px;
                                border:1px solid #ddd;
                            "
                        >
                        """

                price = (
                    listing_value(
                        listing,
                        "price"
                    )
                    or listing_value(
                        listing,
                        "price_label"
                    )
                )

                details = []

                bedrooms = listing_value(
                    listing,
                    "bedrooms",
                    0
                )

                if bedrooms:
                    details.append(
                        f"&#128719; {bedrooms} quartos"
                    )

                bathrooms = listing_value(
                    listing,
                    "bathrooms",
                    0
                )

                if bathrooms:
                    details.append(
                        f"&#128703; {bathrooms} banheiros"
                    )

                property_type = listing_value(
                    listing,
                    "property_type"
                )

                if property_type:
                    details.append(
                        f"&#127969; {property_type}"
                    )

                details_html = ""

                if details:
                    details_html = f"""
                        <p style="
                            color:#374151;
                            margin:0 0 14px 0;
                            font-size:28px;
                            font-weight:600;
                            line-height:1.6;
                        ">
                            {"&nbsp;&nbsp;".join(details)}
                        </p>
                    """

                published_at = listing_value(
                    listing,
                    "published_at"
                )

                published_html = ""

                if published_at:
                    published_html = f"""
                        <p style="
                            color:#6b7280;
                            font-size:22px;
                            line-height:1.5;
                            margin:0 0 14px 0;
                        ">
                            &#128338; {published_at}
                        </p>
                    """

                html += f"""
                <div style="
                    border:1px solid #ddd;
                    border-radius:14px;
                    overflow:hidden;
                    margin-bottom:30px;
                    background:#ffffff;
                    box-shadow:0 8px 24px rgba(17,24,39,0.08);
                ">

                    <img
                        src="{main_image}"
                        style="
                            width:100%;
                            max-width:613px;
                            height:320px;
                            object-fit:cover;
                            display:block;
                        "
                    >

                    <div style="padding:30px;">

                        <div style="
                            margin-bottom:12px;
                            white-space:nowrap;
                            overflow-x:auto;
                        ">
                            {thumbnails_html}
                        </div>

                        <h2 style="
                            margin:0 0 18px 0;
                            color:#111827;
                            font-size:36px;
                            line-height:1.25;
                        ">
                            {listing_value(listing, "title")}
                        </h2>

                        <p style="
                            font-size:32px;
                            font-weight:bold;
                            color:#16a34a;
                            line-height:1.2;
                            margin:0 0 24px 0;
                        ">
                            <span style="font-size:36px;">&#128176;</span>
                            {price}
                        </p>

                        {details_html}

                        {published_html}

                        <a
                            href="{listing_value(listing, "url")}"
                            style="
                                display:inline-block;
                                background:#2563eb;
                                color:#ffffff;
                                text-decoration:none;
                                padding:20px 30px;
                                border-radius:12px;
                                font-weight:bold;
                                font-size:26px;
                                margin-top:18px;
                            "
                        >
                            Ver im&oacute;vel
                        </a>

                    </div>
                </div>
                """

        message = MIMEMultipart()

        message["From"] = EMAIL_USERNAME

        recipients = [
            email.strip()
            for email in EMAIL_TO.split(",")
        ]

        message["To"] = ", ".join(recipients)

        message["Subject"] = (
            "Novos imóveis encontrados"
        )

        message.attach(
            MIMEText(html, "html")
        )

        server = smtplib.SMTP(
            EMAIL_HOST,
            EMAIL_PORT
        )

        server.starttls()

        server.login(
            EMAIL_USERNAME,
            EMAIL_PASSWORD
        )

        server.sendmail(
            EMAIL_USERNAME,
            recipients,
            message.as_string()
        )

        server.quit()

        print("Email enviado.")

    def send_price_changes(
            self,
            changes
    ):

        if not changes:
            return

        html = """
        <h1 style="
            color:#111827;
            font-size:36px;
            line-height:1.2;
            margin-bottom:30px;
        ">
            &#128176; Altera&ccedil;&otilde;es de pre&ccedil;o
        </h1>
        """

        for item in changes:

            listing = item["listing"]

            def listing_value(
                    key,
                    default=""
            ):

                if isinstance(
                    listing,
                    dict
                ):
                    return listing.get(
                        key,
                        default
                    )

                return getattr(
                    listing,
                    key,
                    default
                )

            old_price = int(
                item["old_price"] or 0
            )

            new_price = int(
                item["new_price"] or 0
            )

            is_lower = item["is_lower"]

            color = (
                "#16a34a"
                if is_lower
                else "#dc2626"
            )

            icon = (
                "&#128201;"
                if is_lower
                else "&#128200;"
            )

            status = (
                "BARATEOU"
                if is_lower
                else "FICOU MAIS CARO"
            )

            provider = listing_value(
                "provider"
            )

            details = []

            bedrooms = listing_value(
                "bedrooms",
                0
            )

            if bedrooms:
                details.append(
                    f"&#128719; {bedrooms} quartos"
                )

            bathrooms = listing_value(
                "bathrooms",
                0
            )

            if bathrooms:
                details.append(
                    f"&#128703; {bathrooms} banheiros"
                )

            property_type = listing_value(
                "property_type"
            )

            if property_type:
                details.append(
                    f"&#127969; {property_type}"
                )

            details_html = ""

            if details:
                details_html = f"""
                    <p style="
                        color:#374151;
                        margin:0 0 14px 0;
                        font-size:28px;
                        font-weight:600;
                        line-height:1.6;
                    ">
                        {"&nbsp;&nbsp;".join(details)}
                    </p>
                """

            published_at = listing_value(
                "published_at"
            )

            published_html = ""

            if published_at:
                published_html = f"""
                    <p style="
                        color:#6b7280;
                        font-size:22px;
                        line-height:1.5;
                        margin:0 0 14px 0;
                    ">
                        &#128338; {published_at}
                    </p>
                """

            main_image = listing_value(
                "thumbnail_url"
            )

            thumbnails_html = ""

            image_urls = (
                listing_value(
                    "image_urls",
                    []
                )
                or []
            )

            if image_urls:

                for image in image_urls[1:7]:
                    thumbnails_html += f"""
                    <img
                        src="{image}"
                        style="
                            width:90px;
                            height:70px;
                            object-fit:cover;
                            border-radius:8px;
                            margin-right:6px;
                            border:1px solid #ddd;
                        "
                    >
                    """

            html += f"""
            <div style="
                border:1px solid #ddd;
                border-radius:14px;
                overflow:hidden;
                margin-bottom:30px;
                background:#ffffff;
                box-shadow:0 8px 24px rgba(17,24,39,0.08);
            ">

                <img
                    src="{main_image}"
                    style="
                        width:100%;
                        max-width:613px;
                        height:320px;
                        object-fit:cover;
                        display:block;
                    "
                />

                <div style="padding:30px;">

                    <div style="
                        margin-bottom:12px;
                        white-space:nowrap;
                        overflow-x:auto;
                    ">
                        {thumbnails_html}
                    </div>

                    <h2 style="
                        margin:0 0 18px 0;
                        color:#111827;
                        font-size:36px;
                        line-height:1.25;
                    ">
                        {listing_value("title")}
                    </h2>

                    <p style="
                        color:#6b7280;
                        font-size:24px;
                        line-height:1.5;
                        margin:0 0 24px 0;
                    ">
                        <b>Imobili&aacute;ria:</b> {provider}
                    </p>

                    <p style="
                        margin:0 0 24px 0;
                        font-size:30px;
                        line-height:1.4;
                    ">
                        {icon}
                        <b style="
                            color:{color};
                            font-size:32px;
                        ">
                            {status}
                        </b>
                    </p>

                    <div style="
                        background:#f9fafb;
                        border:1px solid #e5e7eb;
                        border-radius:12px;
                        padding:24px 26px;
                        margin:0 0 28px 0;
                    ">
                        <p style="
                            color:#6b7280;
                            font-size:24px;
                            line-height:1.5;
                            margin:0 0 8px 0;
                        ">
                            De:
                            <s>{format_price(old_price)}</s>
                        </p>

                        <p style="
                            color:{color};
                            font-size:44px;
                            font-weight:bold;
                            line-height:1.2;
                            margin:0;
                        ">
                            Para:
                            {format_price(new_price)}
                        </p>
                    </div>

                    {details_html}

                    {published_html}

                    <a
                        href="{listing_value("url")}"
                        style="
                            display:inline-block;
                            background:{color};
                            color:#ffffff;
                            text-decoration:none;
                            padding:20px 30px;
                            border-radius:12px;
                            font-weight:bold;
                            font-size:26px;
                            margin-top:18px;
                        "
                    >
                        Ver im&oacute;vel
                    </a>

                </div>

            </div>
            """

        message = MIMEMultipart()

        recipients = [
            email.strip()
            for email in EMAIL_TO.split(",")
        ]

        message["From"] = EMAIL_USERNAME

        message["To"] = ", ".join(recipients)

        message["Subject"] = (
            "Alterações de preço detectadas"
        )

        message.attach(
            MIMEText(html, "html")
        )

        server = smtplib.SMTP(
            EMAIL_HOST,
            EMAIL_PORT
        )

        server.starttls()

        server.login(
            EMAIL_USERNAME,
            EMAIL_PASSWORD
        )

        server.sendmail(
            EMAIL_USERNAME,
            recipients,
            message.as_string()
        )

        server.quit()

        print("Email de alteraÃ§Ã£o enviado.")


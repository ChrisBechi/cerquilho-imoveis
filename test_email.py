import smtplib
import ssl

from app.config.settings import (
    EMAIL_HOST,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_USERNAME,
)


def main():
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        print("Configure EMAIL_USERNAME e EMAIL_PASSWORD no .env.")
        return 1

    try:
        with smtplib.SMTP(EMAIL_HOST or "smtp.gmail.com", EMAIL_PORT, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        print("LOGIN OK")
        return 0
    except (smtplib.SMTPException, OSError) as error:
        print(f"Erro no login SMTP: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

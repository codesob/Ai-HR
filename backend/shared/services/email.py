import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from shared.core.config import get_settings

logger = logging.getLogger(__name__)


def email_configured() -> bool:
    return bool(get_settings().smtp_host)


def _send_sync(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> bool:
    """Returns True if delivered to the SMTP server. Never raises."""
    if not email_configured():
        return False
    try:
        await asyncio.to_thread(_send_sync, to, subject, body)
        return True
    except Exception:
        logger.exception("Email delivery failed", extra={"to_domain": to.rsplit("@", 1)[-1]})
        return False


async def send_account_email(to: str, subject: str, body: str, link: str) -> None:
    """Password-reset / verification mail. Without SMTP outside production the link is logged so it can be used."""
    if await send_email(to, subject, f"{body}\n\n{link}\n"):
        return
    if get_settings().is_production:
        logger.error("Account email not delivered; configure SMTP", extra={"to_domain": to.rsplit("@", 1)[-1]})
    else:
        logger.warning("Email not configured. %s for %s: %s", subject, to, link)

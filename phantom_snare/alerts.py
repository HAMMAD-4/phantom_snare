"""Email alert module for phantom_snare."""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
    from .logger import CaptureRecord

_module_logger = logging.getLogger("phantom_snare.alerts")


def send_alert(record: "CaptureRecord", config: "Config") -> None:
    """Send an email alert for a captured connection.

    Does nothing silently if email alerts are not fully configured.

    Args:
        record: The capture event that triggered the alert.
        config: Runtime configuration (must have all SMTP fields set).
    """
    if not config.email_alerts_enabled:
        return

    subject = (
        f"[phantom_snare] Intrusion attempt from {record.remote_ip}:{record.remote_port} "
        f"on port {record.local_port}"
    )
    body = (
        f"phantom_snare detected a connection:\n\n"
        f"  Timestamp : {record.timestamp.isoformat()}\n"
        f"  Source    : {record.remote_ip}:{record.remote_port}\n"
        f"  Honeypot  : port {record.local_port}\n"
        f"  Payload   : {len(record.payload)} bytes\n\n"
        f"--- Payload (UTF-8, errors replaced) ---\n"
        f"{record.payload_text()}\n"
        f"--- End of payload ---\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.alert_email_from  # type: ignore[assignment]
    msg["To"] = config.alert_email_to  # type: ignore[assignment]

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(config.alert_smtp_host, config.alert_smtp_port) as smtp:  # type: ignore[arg-type]
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(config.alert_smtp_user, config.alert_smtp_password)  # type: ignore[arg-type]
            smtp.sendmail(
                config.alert_email_from,  # type: ignore[arg-type]
                config.alert_email_to,  # type: ignore[arg-type]
                msg.as_string(),
            )
    except Exception as exc:  # pylint: disable=broad-except
        _module_logger.warning("Failed to send email alert: %s", exc)

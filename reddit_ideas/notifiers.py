"""Notification adapters for delivering the weekly/daily report.

``Notifier`` is a structural Protocol so any object with a matching ``send``
signature works without inheriting from a base class.  ``build_notifier``
reads the app config and wires up whichever channels are configured; if
neither SMTP nor Telegram is set the pipeline simply skips notification.
"""
from __future__ import annotations

import json
import smtplib
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from .config import AppConfig


class Notifier(Protocol):
    """Protocol for report delivery channels.

    Input:
        subject: Notification subject line.
        body: Notification body text.
        report_path: Path to generated markdown report.

    Output:
        None. Implementations should raise on delivery failure.
    """

    def send(self, subject: str, body: str, report_path: Path) -> None: ...


@dataclass(slots=True)
class EmailNotifier:
    """SMTP notifier that sends report emails with optional attachment.

    Inputs:
        host: SMTP hostname.
        port: SMTP port number.
        user: SMTP username and sender email.
        password: SMTP password or app password.
        email_to: Recipient email address.
    """

    host: str
    port: int
    user: str
    password: str
    email_to: str

    def send(self, subject: str, body: str, report_path: Path) -> None:
        """Send an email for the report.

        Args:
            subject: Subject line for the email.
            body: Plain-text body content.
            report_path: Markdown report file path to attach when available.

        Returns:
            None.
        """

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.user
        message["To"] = self.email_to
        message.set_content(body)

        if report_path.exists():
            message.add_attachment(
                report_path.read_bytes(),
                maintype="text",
                subtype="markdown",
                filename=report_path.name,
            )

        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(self.user, self.password)
            smtp.send_message(message)


@dataclass(slots=True)
class TelegramNotifier:
    """Telegram bot notifier for compact text summaries.

    Inputs:
        bot_token: Telegram bot token.
        chat_id: Destination chat/channel id.
    """

    bot_token: str
    chat_id: str

    def send(self, subject: str, body: str, report_path: Path) -> None:
        """Send summary text to Telegram.

        Args:
            subject: Notification subject text.
            body: Summary body text.
            report_path: Unused in Telegram mode; kept for protocol parity.

        Returns:
            None.
        """

        text = f"{subject}\n\n{body[:3500]}"
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}
        data = urllib.parse.urlencode(payload).encode("utf-8")
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        request = urllib.request.Request(url=url, data=data, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            if not parsed.get("ok"):
                raise RuntimeError("Telegram API returned non-ok response")


class CompositeNotifier:
    """Fan-out notifier that forwards to all configured channels.

    Input:
        channels: Concrete notifier implementations to invoke in order.
    """

    def __init__(self, channels: list[Notifier]) -> None:
        """Store notifier channels.

        Args:
            channels: List of channels that implement ``Notifier``.

        Returns:
            None.
        """

        self.channels = channels

    def send(self, subject: str, body: str, report_path: Path) -> None:
        """Dispatch the same payload to each channel.

        Args:
            subject: Notification subject line.
            body: Notification body text.
            report_path: Generated report path.

        Returns:
            None.
        """

        for channel in self.channels:
            channel.send(subject, body, report_path)


def build_notifier(config: AppConfig) -> CompositeNotifier | None:
    """Build notifier channels from config.

    Args:
        config: Application config with optional SMTP/Telegram sections.

    Returns:
        ``CompositeNotifier`` when at least one channel is configured,
        otherwise None.
    """

    channels: list[Notifier] = []
    if config.smtp:
        channels.append(
            EmailNotifier(
                host=config.smtp.host,
                port=config.smtp.port,
                user=config.smtp.user,
                password=config.smtp.password,
                email_to=config.smtp.email_to,
            )
        )
    if config.telegram:
        channels.append(
            TelegramNotifier(
                bot_token=config.telegram.bot_token,
                chat_id=config.telegram.chat_id,
            )
        )
    if not channels:
        return None
    return CompositeNotifier(channels)

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
    def send(self, subject: str, body: str, report_path: Path) -> None: ...


@dataclass(slots=True)
class EmailNotifier:
    host: str
    port: int
    user: str
    password: str
    email_to: str

    def send(self, subject: str, body: str, report_path: Path) -> None:
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
    bot_token: str
    chat_id: str

    def send(self, subject: str, body: str, report_path: Path) -> None:
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
    def __init__(self, channels: list[Notifier]) -> None:
        self.channels = channels

    def send(self, subject: str, body: str, report_path: Path) -> None:
        for channel in self.channels:
            channel.send(subject, body, report_path)


def build_notifier(config: AppConfig) -> CompositeNotifier | None:
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

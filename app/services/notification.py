from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

from app.core.config import get_settings
from app.models import WatchSignal


@dataclass(frozen=True)
class NotificationResult:
    sent: bool
    error: str = ""


class NotificationService:
    def __init__(self):
        self.settings = get_settings()

    def notify_buy_signal(
        self,
        signal: WatchSignal,
        *,
        trading_system_name: str | None = None,
        rule_name: str | None = None,
    ) -> NotificationResult:
        if signal.notification_sent:
            return NotificationResult(sent=False, error="")
        if signal.signal_type != "buy":
            return NotificationResult(sent=False, error="only buy signal notification is supported")

        subject, body = self._buy_signal_template(
            signal,
            trading_system_name=trading_system_name,
            rule_name=rule_name,
        )
        try:
            self._send_email(subject, body)
        except Exception as exc:
            error = str(exc)[:1000]
            signal.notification_sent = False
            signal.notification_error = error
            return NotificationResult(sent=False, error=error)

        signal.notification_sent = True
        signal.notification_sent_at = datetime.utcnow()
        signal.notification_error = None
        return NotificationResult(sent=True)

    def notify_trade_signal(
        self,
        signal: WatchSignal,
        *,
        trading_system_name: str | None = None,
        rule_name: str | None = None,
    ) -> NotificationResult:
        if signal.notification_sent:
            return NotificationResult(sent=False, error="")
        if signal.signal_type not in {"sell", "risk"}:
            return NotificationResult(sent=False, error="only sell/risk trade signal notification is supported")

        subject, body = self._trade_signal_template(
            signal,
            trading_system_name=trading_system_name,
            rule_name=rule_name,
        )
        try:
            self._send_email(subject, body)
        except Exception as exc:
            error = str(exc)[:1000]
            signal.notification_sent = False
            signal.notification_error = error
            return NotificationResult(sent=False, error=error)

        signal.notification_sent = True
        signal.notification_sent_at = datetime.utcnow()
        signal.notification_error = None
        return NotificationResult(sent=True)

    def _send_email(self, subject: str, body: str) -> None:
        settings = self.settings
        if not settings.email_enabled:
            raise RuntimeError("email notification is disabled")
        missing = [
            name
            for name, value in {
                "SMTP_HOST": settings.smtp_host,
                "SMTP_FROM": settings.smtp_from,
                "SMTP_TO": settings.smtp_to,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"email config missing: {', '.join(missing)}")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = settings.smtp_to
        message.set_content(body)

        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with server:
            if settings.smtp_port != 465 and settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)

    def _buy_signal_template(
        self,
        signal: WatchSignal,
        *,
        trading_system_name: str | None,
        rule_name: str | None,
    ) -> tuple[str, str]:
        system_text = trading_system_name or signal.trading_system_code or signal.trading_system or "-"
        rule_text = rule_name or signal.rule_code or signal.buy_point_type or "-"
        trigger_time = signal.trigger_time.isoformat(sep=" ", timespec="seconds") if signal.trigger_time else "-"
        link = f"{self.settings.app_base_url.rstrip('/')}/watch-pool"
        subject = f"[Aquant] 买点信号提醒：{signal.stock_name or signal.stock_code}"
        body = "\n".join(
            [
                "Aquant 买点信号提醒",
                "",
                f"股票名称：{signal.stock_name or '-'}",
                f"股票代码：{signal.stock_code}",
                f"交易体系：{system_text}",
                f"规则名称：{rule_text}",
                f"触发价：{signal.trigger_price if signal.trigger_price is not None else '-'}",
                f"触发时间：{trigger_time}",
                f"触发原因：{signal.trigger_reason or '-'}",
                "",
                f"系统链接：{link}",
                "提示：该信号仅作交易辅助，请结合个人交易规则确认。",
            ]
        )
        return subject, body

    def _trade_signal_template(
        self,
        signal: WatchSignal,
        *,
        trading_system_name: str | None,
        rule_name: str | None,
    ) -> tuple[str, str]:
        system_text = trading_system_name or signal.trading_system_code or signal.trading_system or "-"
        rule_text = rule_name or signal.rule_code or signal.buy_point_type or "-"
        trigger_time = signal.trigger_time.isoformat(sep=" ", timespec="seconds") if signal.trigger_time else "-"
        link = f"{self.settings.app_base_url.rstrip('/')}/watch-pool"
        signal_label = "止损提醒" if signal.rule_type == "stop_loss" else "卖点提醒"
        subject = f"[Aquant] {signal_label}：{signal.stock_name or signal.stock_code}"
        body = "\n".join(
            [
                f"Aquant {signal_label}",
                "",
                f"股票名称：{signal.stock_name or '-'}",
                f"股票代码：{signal.stock_code}",
                f"交易体系：{system_text}",
                f"规则名称：{rule_text}",
                f"触发价：{signal.trigger_price if signal.trigger_price is not None else '-'}",
                f"触发时间：{trigger_time}",
                f"触发原因：{signal.trigger_reason or '-'}",
                "",
                f"系统链接：{link}",
                "提示：该信号不会自动卖出，请人工确认。",
            ]
        )
        return subject, body

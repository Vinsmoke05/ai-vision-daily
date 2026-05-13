import logging

import requests

from .config import Settings

logger = logging.getLogger("news_digest.publisher")

MAX_MSG_LEN = 4096


def _split_digest(digest: str) -> list[str]:
    chunks: list[str] = []
    current = ""

    for line in digest.split("\n"):
        candidate = f"{current}\n{line}".strip()
        if len(candidate) > MAX_MSG_LEN:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks or [digest]


def publish_telegram(digest: str, settings: Settings) -> bool:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    chunks = _split_digest(digest)

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id": settings.telegram_channel_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info("Telegram msg %d/%d sent (%d chars)", i + 1, len(chunks), len(chunk))
        except Exception:
            logger.exception("Telegram msg %d/%d failed", i + 1, len(chunks))
            try:
                payload.pop("parse_mode", None)
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                logger.info("Fallback plain text msg %d sent", i + 1)
            except Exception:
                logger.exception("Fallback also failed")
                return False
    return True


def publish_wechat_work(digest: str, settings: Settings) -> bool:
    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={settings.wechat_work_bot_key}"
    chunks = _split_digest(digest)

    for i, chunk in enumerate(chunks):
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": chunk},
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") != 0:
                logger.error("WeChat Work API error: %s", result.get("errmsg"))
                return False
            logger.info("WeChat Work msg %d/%d sent (%d chars)", i + 1, len(chunks), len(chunk))
        except Exception:
            logger.exception("WeChat Work msg %d/%d failed", i + 1, len(chunks))
            return False
    return True


def publish(digest: str, settings: Settings, fallback_raw: str | None = None) -> bool:
    content = digest or fallback_raw
    if not content:
        logger.warning("Nothing to publish")
        return False

    if settings.push_channel == "wechat_work":
        if not settings.wechat_work_bot_key:
            logger.error("WECHAT_WORK_BOT_KEY not configured")
            return False
        return publish_wechat_work(content, settings)
    elif settings.push_channel == "telegram":
        if not settings.telegram_bot_token or not settings.telegram_channel_id:
            logger.error("Telegram credentials not configured")
            return False
        return publish_telegram(content, settings)
    else:
        logger.error("Unknown push_channel: %s", settings.push_channel)
        return False

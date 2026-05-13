import logging
from datetime import datetime, timezone

import requests

from .config import Settings

logger = logging.getLogger("news_digest.summarizer")

SYSTEM_PROMPT = """你是一个 AI 工业视觉领域的新闻编辑。请将以下收集到的技术资讯整理成一份简洁的每日早报。

要求：
1. 按主题分类（如：模型发布、开源项目、技术突破、行业动态）
2. 每条资讯用 1-2 句话概括核心信息
3. 保留原文链接
4. 使用中文输出
5. 格式为 Markdown，适合在 Telegram 上阅读"""


def summarize(raw_digest: str, settings: Settings) -> str | None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"以下是 {today} 的原始资讯汇总，请帮我整理成早报：\n\n{raw_digest}",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        resp = requests.post(
            settings.llm_api_url,
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        logger.info("LLM summary generated: %d chars", len(result))
        return result
    except Exception:
        logger.exception("LLM summarization failed")
        return None

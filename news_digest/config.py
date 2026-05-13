from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Push channel: "telegram" or "wechat_work"
    push_channel: str = "telegram"

    # Telegram
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    # WeChat Work (only needed if push_channel == "wechat_work")
    wechat_work_bot_key: str = ""

    # LLM
    llm_api_key: str
    llm_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    llm_model: str = "deepseek-chat"

    # Scraper config
    gh_trending_languages: list[str] = ["python", "cpp", "jupyter-notebook"]
    reddit_subreddits: list[str] = ["computervision", "artificial", "MachineLearning"]
    opencv_check_releases: bool = True
    deepseek_news_url: str = "https://api-docs.deepseek.com/news"

    # Paths
    cache_db_path: str = str(Path(__file__).resolve().parent.parent / "cache.db")
    log_dir: str = str(Path(__file__).resolve().parent.parent / "logs")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

from pathlib import Path
import os


PROJECT_DIR = Path(__file__).resolve().parents[2]
GENERATED_DIR = PROJECT_DIR / "generated"
JOBS_DIR = GENERATED_DIR / "jobs"

PIPELINE_VERSION = "0.1.0"
AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "mock").lower()
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")

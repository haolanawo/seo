"""DeepSeek API 封装 —— 异步调用、并发控制、超时重试。"""

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger("api")

# ---------- 配置 ----------
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
TIMEOUT = 120  # 单次请求超时秒数
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # 指数退避秒数
MAX_CONCURRENT = 5

_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphore


_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=TIMEOUT)
    return _client


async def generate_text(prompt: str) -> str:
    """调用 DeepSeek API 生成文本，带并发控制和自动重试。"""
    sem = _get_semaphore()
    client = _get_client()

    async with sem:
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(f"API 调用失败（第{attempt+1}次），{delay}s 后重试: {e}")
                    await asyncio.sleep(delay)

        logger.error(f"API 调用在 {MAX_RETRIES} 次重试后仍然失败: {last_error}")
        raise last_error  # type: ignore[misc]

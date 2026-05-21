"""文章生成核心逻辑 —— 拼装 prompt、调用 API、保存文件、记录日志。"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from api import generate_text
from config_loader import ROOT, build_diversity_prompt, load_yaml

logger = logging.getLogger("generate")

OUTPUT_ROOT = ROOT / "output"
LOG_ROOT = ROOT / "logs"


def _load_template(template_path: str | None) -> str:
    """加载 .md 模板文件内容。"""
    if not template_path:
        return ""
    full = ROOT / template_path
    if full.exists():
        return full.read_text(encoding="utf-8")
    logger.warning(f"模板文件不存在: {template_path}")
    return ""


def _assemble_prompt(
    diversity_prompt: str,
    platform_style: str,
    template: str,
    emphasis: str,
) -> str:
    """按顺序拼接最终 prompt。"""
    parts = [diversity_prompt, platform_style, template, emphasis]
    return "\n\n---\n\n".join(p for p in parts if p)


def _write_log(entry: dict) -> None:
    """写入一行 JSON 日志到 logs/{date}.log。"""
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_file = LOG_ROOT / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    import json

    line = json.dumps(entry, ensure_ascii=False)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def generate_articles(
    platform: str,
    count: int,
    template_path: str | None = None,
) -> str:
    """
    生成 count 篇文章，保存到 output/{platform}_{timestamp}/ 目录。
    返回输出文件夹路径。
    """
    # 加载配置
    diversity = load_yaml("config/diversity.yaml")
    platform_cfg = load_yaml(f"config/platforms/{platform}.yaml")
    platform_style = platform_cfg.get("style_prompt", "")
    emphasis = platform_cfg.get("emphasis", "")
    template = _load_template(template_path)

    # 创建输出文件夹
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_ROOT / f"{platform}_{ts}"
    folder.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(5)

    async def generate_one(index: int):
        async with sem:
            diversity_prompt, meta = build_diversity_prompt(diversity, selection)
            full_prompt = _assemble_prompt(diversity_prompt, platform_style, template, emphasis)

            t0 = time.time()
            status = "ok"
            error_msg = ""
            try:
                content = await generate_text(full_prompt)
            except Exception as e:
                content = ""
                status = "error"
                error_msg = str(e)

            elapsed = round(time.time() - t0, 2)

            # 保存文章
            filename = f"{index + 1:03d}.md"
            filepath = folder / filename
            header = (
                f"# 生成 #{index + 1}\n"
                f"平台: {platform_cfg.get('name', platform)}\n"
                f"人物定位: {meta['persona']}\n"
                f"场景: {meta['scene']}\n"
                f"论点切入: {meta['angle']}\n"
                f"主关键词: {meta['main_keyword']}\n"
                f"辅助关键词: {meta['auxiliary_keyword']}\n"
                f"生成时间: {datetime.now().isoformat()}\n"
                f"状态: {status}\n\n"
                "---\n\n"
            )
            filepath.write_text(header + content, encoding="utf-8")

            # 日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "platform": platform,
                "index": index + 1,
                "status": status,
                "elapsed_s": elapsed,
                "main_keyword": meta["main_keyword"],
                "auxiliary_keyword": meta["auxiliary_keyword"],
                "error": error_msg,
                "file": str(filepath),
            }
            _write_log(log_entry)

            return {"index": index + 1, "status": status, "elapsed": elapsed, "file": str(filepath), "error": error_msg}

    tasks = [generate_one(i) for i in range(count)]
    results = await asyncio.gather(*tasks)
    return str(folder), results


async def generate_articles_stream(
    platform: str,
    count: int,
    template_path: str | None = None,
    selection: dict | None = None,
):
    """
    流式生成 —— 每完成一篇就 yield 进度事件，适用于 SSE 推送。
    selection 为 {"persona": [...], ...}，限制每类的随机抽取范围。
    """
    import json

    # 加载配置
    diversity = load_yaml("config/diversity.yaml")
    platform_cfg = load_yaml(f"config/platforms/{platform}.yaml")
    platform_style = platform_cfg.get("style_prompt", "")
    emphasis = platform_cfg.get("emphasis", "")
    template = _load_template(template_path)

    # 创建输出文件夹
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = OUTPUT_ROOT / f"{platform}_{ts}"
    folder.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(5)

    async def generate_one(index: int):
        async with sem:
            yield {"type": "progress", "index": index + 1, "status": "generating"}

            diversity_prompt, meta = build_diversity_prompt(diversity, selection)
            full_prompt = _assemble_prompt(diversity_prompt, platform_style, template, emphasis)

            t0 = time.time()
            status = "ok"
            error_msg = ""
            try:
                content = await generate_text(full_prompt)
            except Exception as e:
                content = ""
                status = "error"
                error_msg = str(e)

            elapsed = round(time.time() - t0, 2)

            # 保存文章
            filename = f"{index + 1:03d}.md"
            filepath = folder / filename
            header = (
                f"# 生成 #{index + 1}\n"
                f"平台: {platform_cfg.get('name', platform)}\n"
                f"人物定位: {meta['persona']}\n"
                f"场景: {meta['scene']}\n"
                f"论点切入: {meta['angle']}\n"
                f"主关键词: {meta['main_keyword']}\n"
                f"辅助关键词: {meta['auxiliary_keyword']}\n"
                f"生成时间: {datetime.now().isoformat()}\n"
                f"状态: {status}\n\n"
                "---\n\n"
            )
            filepath.write_text(header + content, encoding="utf-8")

            # 日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "platform": platform,
                "index": index + 1,
                "status": status,
                "elapsed_s": elapsed,
                "main_keyword": meta["main_keyword"],
                "auxiliary_keyword": meta["auxiliary_keyword"],
                "error": error_msg,
                "file": str(filepath),
            }
            _write_log(log_entry)

            yield {
                "type": "progress",
                "index": index + 1,
                "status": status,
                "elapsed": elapsed,
                "file": str(filepath),
                "error": error_msg,
            }

    async def run_all():
        # 并发执行，通过队列收集进度
        queue: asyncio.Queue = asyncio.Queue()

        async def worker(i: int):
            async for event in generate_one(i):
                await queue.put(event)

        worker_tasks = [asyncio.create_task(worker(i)) for i in range(count)]

        # 等所有 worker 完成
        done = 0
        while done < count:
            event = await queue.get()
            if event["type"] == "progress" and event.get("status") in ("ok", "error"):
                done += 1
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        await asyncio.gather(*worker_tasks)

        yield f"data: {json.dumps({'type': 'complete', 'folder': str(folder), 'count': count}, ensure_ascii=False)}\n\n"

    return run_all()

"""FastAPI 主入口 —— 本地 Web 前端 + API 路由。"""

import json
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config_loader import ROOT, get_diversity_options, save_yaml
from generate import generate_articles_stream

app = FastAPI(title="多平台推广文章生成器")

# ---------- 静态文件 & 模板 ----------
static_dir = ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(ROOT / "frontend"))


# ==================== 辅助 ====================

def _read_raw(path: str) -> str:
    full = ROOT / path
    if not full.exists():
        raise HTTPException(404, f"文件不存在: {path}")
    return full.read_text(encoding="utf-8")


def _save_yaml_text(path: str, yaml_text: str) -> None:
    data = yaml.safe_load(yaml_text)
    if data is None:
        raise HTTPException(400, "YAML 解析失败：内容为空或格式错误")
    save_yaml(path, data)


# ==================== 页面 ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    platforms = [
        {"key": "zhihu", "name": "知乎"},
        {"key": "xiaohongshu", "name": "小红书"},
        {"key": "x", "name": "X"},
        {"key": "bilibili", "name": "Bilibili"},
    ]
    return templates.TemplateResponse(request, "index.html", {"platforms": platforms})


# ==================== 配置 API ====================

@app.get("/api/config/diversity")
async def get_diversity_config():
    return {"yaml_text": _read_raw("config/diversity.yaml")}


@app.get("/api/config/platforms/{name}")
async def get_platform_config(name: str):
    return {"yaml_text": _read_raw(f"config/platforms/{name}.yaml")}


@app.post("/api/config/diversity")
async def save_diversity_config(payload: dict):
    _save_yaml_text("config/diversity.yaml", payload["yaml_text"])
    return {"status": "ok"}


@app.post("/api/config/platforms/{name}")
async def save_platform_config(name: str, payload: dict):
    _save_yaml_text(f"config/platforms/{name}.yaml", payload["yaml_text"])
    return {"status": "ok"}


# ==================== 多样性选项 API ====================

@app.get("/api/diversity/options")
async def diversity_options():
    """返回多样性配置的结构化选项列表，供前端渲染勾选框。"""
    return get_diversity_options()


# ==================== 生成 API ====================

@app.post("/api/generate")
async def generate(payload: dict):
    """
    POST 方式生成文章，返回 SSE 流。
    body: {"platform": "zhihu", "count": 3, "template": "", "selection": {...}}
    """
    platform = payload.get("platform", "zhihu")
    count = payload.get("count", 1)
    template = payload.get("template") or None
    selection = payload.get("selection") or None

    async def event_stream():
        gen = await generate_articles_stream(platform, count, template, selection)
        async for event in gen:
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ==================== 日志 API ====================

@app.get("/api/logs")
async def get_logs(date: str = ""):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    log_file = ROOT / "logs" / f"{date}.log"
    if not log_file.exists():
        return {"logs": []}
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    return {"logs": [json.loads(line) for line in lines if line]}


# ==================== 模板 API ====================

@app.get("/api/templates")
async def list_templates():
    tp_dir = ROOT / "templates"
    if not tp_dir.exists():
        return {"templates": []}
    files = sorted(tp_dir.glob("*.md"))
    return {"templates": [f"templates/{f.name}" for f in files]}


# ==================== 启动入口 ====================

def main():
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()

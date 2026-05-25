"""FastAPI 主入口 —— 本地 Web 前端 + API 路由。"""

import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config_loader import ROOT, get_diversity_options
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
    # 先验证 YAML 是否可以解析
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"YAML 解析失败: {e}")
    if data is None:
        raise HTTPException(400, "YAML 解析失败：内容为空")
    # 验证通过，直接写入原始文本，保留用户的格式和注释
    full = ROOT / path
    full.write_text(yaml_text, encoding="utf-8")


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


# ==================== 输出列表 API ====================

@app.get("/api/outputs")
async def list_outputs():
    """列出 output 下所有文件夹，按时间倒序，供历史下载。"""
    output_dir = ROOT / "output"
    if not output_dir.exists():
        return {"folders": []}
    folders = []
    for d in sorted(output_dir.iterdir(), reverse=True):
        if d.is_dir():
            files = list(d.glob("*.md"))
            md_count = sum(1 for f in files if not f.name.endswith("_prompt.md"))
            folders.append({
                "name": d.name,
                "md_count": md_count,
            })
    return {"folders": folders}


# ==================== 下载 API ====================

@app.get("/api/download/{folder_name}")
async def download_folder(folder_name: str):
    """将 output 下的指定文件夹打包为 zip 下载。"""
    output_dir = (ROOT / "output").resolve()
    folder = (ROOT / "output" / folder_name).resolve()
    # 防止路径穿越攻击
    if not str(folder).startswith(str(output_dir)):
        raise HTTPException(403, "禁止访问")
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(404, "文件夹不存在")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(folder.iterdir()):
            if f.is_file():
                zf.write(f, f.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{folder_name}.zip"'},
    )


# ==================== 启动入口 ====================

def main():
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()

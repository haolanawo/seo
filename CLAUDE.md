# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

## 项目概述

本地 Web 工具，为 bewild.ai（AI 代订阅平台）生成多平台推广文章。后端调用 DeepSeek API（通过 OpenAI SDK 兼容接口），结合随机抽取的多样性参数，生成风格各异的文章，避免内容雷同。

## 常用命令

```bash
# 启动应用（带热重载）
python main.py

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env  # 然后填写 DEEPSEEK_API_KEY
```

应用启动后访问 `http://127.0.0.1:8000`。

**坑：`uvicorn --reload` 不会刷新 `__pycache__/*.pyc`。** 修改代码后如果发现行为没变，先清缓存再重启：
```bash
rm -rf __pycache__ && python main.py
```

## 架构

```
浏览器 (SSE 消费) → FastAPI (main.py) → generate.py → api.py (DeepSeek)
                          ↓                    ↓
                   config_loader.py      文件系统 (output/, logs/)
```

**4 个 Python 文件，无数据库，无状态** —— 后端总计不到 300 行：

| 文件 | 职责 |
|---|---|
| `main.py` | FastAPI 入口：提供 SPA 页面、配置 CRUD 的 REST 接口 + SSE 生成接口、挂载静态文件 |
| `api.py` | DeepSeek API 封装：全局 AsyncOpenAI 单例、asyncio.Semaphore(5) 控制并发、最多 3 次重试（指数退避 2s/4s/8s）、120s 超时 |
| `config_loader.py` | YAML 加载、从多样性配置池中随机抽取、prompt 拼接。核心是 `build_diversity_prompt()` —— 从每类（人物/场景/AI熟悉度/角度/关键词）随机抽一项，拼成 prompt 块 |
| `generate.py` | 批量生成调度：加载配置、创建 `output/{平台}_{时间戳}/` 目录、Semaphore(5) 并发生成、保存纯净 `.md` 文件（仅模型输出）、同时保存 `_prompt.md` 完整 prompt 副本、生成后违禁词检测、写 JSONL 日志到 `logs/{日期}.log`、yield SSE 进度事件 |

## 关键设计决策

- **Prompt 用字符串拼接，不用模板引擎。** 顺序：diversity_prompt + `---` + platform_style + `---` + 可选 template + `---` + emphasis。prompt 内部不做 Jinja2 或占位符替换。
- **YAML 保存避开 yaml.dump。** 保存配置时先用 `yaml.safe_load()` 验证合法性，然后用 `write_text()` 直接写入原始文本，不经过 `yaml.dump()` 往返，以保留用户格式、注释和 block scalar `|` 语法。
- **用 SSE 而非 WebSocket。** 生成结果通过 Server-Sent Events 推送到浏览器。每完成一篇推送 `progress` 事件，全部完成推送 `complete` 事件。
- **三种生成状态：** `ok`（成功）、`banned`（已生成但命中违禁词）、`error`（API 异常）。banned 的文章照常保存，头部注明命中词。
- **前端关键词勾选控制随机池范围。** 用户按类别勾选/取消 chip，只有勾选的项进入随机抽取池。某类全不选时，从全量候选中抽取。
- **原生 JS 单页应用。** 无框架 —— `static/app.js` 负责 tab 切换、配置 CRUD、关键词 chip 渲染、SSE 消费、日志展示。

## 项目约定

- 暂无测试，当前不要求编写测试。
- 不做文章去重、相似度检测、模型 fallback 链。
- YAML 配置中多行字符串统一使用 block scalar `|`（如 style_prompt、product_info）。
- 文件编码始终为 UTF-8。
- 金额约定：人民币直接写数字（"140"），美元写"X刀"（"20刀"）。

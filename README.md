# 多平台推广文章生成器

基于 DeepSeek API 的多平台推广文章批量生成工具，为 bewild.ai 生成风格多样的 SEO 文章。

## 快速开始

### 1. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
copy .env.example .env
```

编辑 `.env`，把 `your_api_key_here` 替换为真实的 API Key。

### 2. 安装依赖

```bash
# 创建虚拟环境（可选）
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动

```bash
python main.py
```

本机浏览器访问 `http://127.0.0.1:8080`。

同一局域网内的其他设备，通过本机 IP 访问（如 `http://192.168.1.100:8000`）。

### Windows 一键启动

双击 `start.bat`，自动创建虚拟环境、安装依赖、启动服务。

## 目录结构

```
├── config/                 # YAML 配置文件
│   ├── diversity.yaml      # 多样性配置（人物/场景/关键词/违禁词等）
│   └── platforms/          # 各平台风格配置
├── frontend/index.html     # 前端页面（Jinja2 模板）
├── static/                 # 前端 JS/CSS
├── templates/              # MD 模板文件（可选参考）
├── api.py                  # DeepSeek API 封装
├── config_loader.py        # 配置加载 + 随机抽取
├── generate.py             # 批量生成调度
├── main.py                 # FastAPI 入口
├── requirements.txt        # Python 依赖
└── .env.example            # 环境变量模板
```

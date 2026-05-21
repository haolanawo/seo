"""配置文件加载工具 —— 读取/写入 YAML，随机抽取配置项。"""

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).parent

# 多样性配置中可随机抽取的列表类字段
DIVERSITY_KEYS = ["persona", "scene", "angle", "main_keywords", "auxiliary_keywords"]


def load_yaml(path: str) -> dict:
    full = ROOT / path
    with open(full, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: str, data: dict) -> None:
    full = ROOT / path
    with open(full, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_diversity_options() -> dict[str, list[str]]:
    """返回多样性配置中所有可选项（供前端渲染勾选框）。"""
    diversity = load_yaml("config/diversity.yaml")
    options = {}
    for key in DIVERSITY_KEYS:
        val = diversity.get(key, [])
        if isinstance(val, list):
            options[key] = [str(v) for v in val]
        else:
            options[key] = [str(val)] if val else []
    options["product_info"] = diversity.get("product_info", "")
    options["forbidden_words"] = diversity.get("forbidden_words", [])
    return options


def _pick(items: list[str], selection: list[str] | None) -> str:
    """从 items 中随机抽取。若 selection 非空则限制范围。"""
    pool = selection if selection else items
    if not pool:
        return ""
    return random.choice(pool)


def build_diversity_prompt(diversity: dict, selection: dict | None = None) -> tuple[str, dict]:
    """
    随机抽取多样性配置拼成 prompt。
    selection 为 {"persona": [...], "scene": [...], ...}，限制每类的抽取范围。
    若 selection 缺失或某 key 为空，则从全部候选中抽取。
    """
    sel = selection or {}

    persona = _pick(diversity.get("persona", []), sel.get("persona"))
    scene = _pick(diversity.get("scene", []), sel.get("scene"))
    angle = _pick(diversity.get("angle", []), sel.get("angle"))
    main_kw = _pick(diversity.get("main_keywords", []), sel.get("main_keywords"))
    aux_kw = _pick(diversity.get("auxiliary_keywords", []), sel.get("auxiliary_keywords"))
    product_info = diversity.get("product_info", "")

    prompt = (
        f"{persona}\n\n"
        f"{scene}\n\n"
        f"{angle}\n\n"
        f"主要围绕关键词：{main_kw}\n"
        f"辅助关键词：{aux_kw}\n\n"
        f"【产品信息】\n{product_info}"
    )

    meta = {
        "persona": persona,
        "scene": scene,
        "angle": angle,
        "main_keyword": main_kw,
        "auxiliary_keyword": aux_kw,
    }
    return prompt, meta

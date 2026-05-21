"""配置文件加载工具 —— 读取/写入 YAML，随机抽取配置项。"""

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).parent


def load_yaml(path: str) -> dict:
    """加载 YAML 文件，返回字典。"""
    full = ROOT / path
    with open(full, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: str, data: dict) -> None:
    """将字典保存为 YAML 文件。"""
    full = ROOT / path
    with open(full, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def pick_random(config: dict, key: str) -> str:
    """从配置中某个列表字段随机抽取一项。如果不是列表则直接返回字符串。"""
    val = config.get(key, "")
    if isinstance(val, list):
        return random.choice(val) if val else ""
    return str(val) if val else ""


def build_diversity_prompt(diversity: dict) -> tuple[str, dict]:
    """随机抽取各类多样性配置，返回 (prompt文本, 元数据字典)。"""
    persona = pick_random(diversity, "persona")
    scene = pick_random(diversity, "scene")
    angle = pick_random(diversity, "angle")
    main_kw = pick_random(diversity, "main_keywords")
    aux_kw = pick_random(diversity, "auxiliary_keywords")
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

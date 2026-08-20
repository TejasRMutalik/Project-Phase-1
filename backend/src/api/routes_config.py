import os
from typing import Dict, Any

import yaml
from fastapi import APIRouter, HTTPException

from src.api.shared import CONFIG_PATH

router = APIRouter()


@router.get("/api/config")
async def get_config():
    """Read current configuration settings."""
    if not os.path.exists(CONFIG_PATH):
        raise HTTPException(status_code=404, detail="Config file not found")
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def _deep_merge(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@router.post("/api/config")
async def update_config(new_config: Dict[str, Any]):
    """Merge partial config updates into default.yaml - a partial payload (e.g. just
    `model`) must not delete sections (`anpr`, `violations`, ...) it didn't mention."""
    try:
        current = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                current = yaml.safe_load(f) or {}
        merged = _deep_merge(current, new_config)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(merged, f, default_flow_style=False)
        return {"status": "success", "message": "Configuration updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

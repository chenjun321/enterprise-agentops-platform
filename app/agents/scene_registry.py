import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


REGISTRY_PATH = Path(__file__).with_name("scene_registry") / "customer_qa_scenes.json"


@lru_cache
def load_customer_qa_scene_registry() -> Dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def match_customer_qa_intent(message: str) -> str:
    registry = load_customer_qa_scene_registry()
    lowered = message.lower()
    for intent, scene in registry["scenes"].items():
        keywords = scene.get("keywords", [])
        if keywords and any(keyword.lower() in lowered for keyword in keywords):
            return intent
    return registry["default_intent"]


def get_customer_qa_scene(intent: str) -> Dict[str, Any]:
    registry = load_customer_qa_scene_registry()
    return registry["scenes"].get(intent, registry["scenes"][registry["default_intent"]])


def get_missing_fields_for_scene(scene: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for mode in scene.get("required_context_modes", []):
        if mode == "order_or_trace":
            if not context.get("order_no") and not context.get("trace_id"):
                missing.append("order_no_or_trace_id")
    return missing

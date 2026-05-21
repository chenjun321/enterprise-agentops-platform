import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


REGISTRY_PATH = Path(__file__).with_name("scene_registry") / "customer_qa_scenes.json"
SCHEMA_PATH = Path(__file__).with_name("scene_registry") / "customer_qa_workflow.schema.json"


@lru_cache
def load_customer_qa_scene_registry() -> Dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_customer_qa_scene_registry(registry, schema)
    return registry


def validate_customer_qa_scene_registry(registry: Dict[str, Any], schema: Dict[str, Any]) -> None:
    for field in schema["required_top_level_fields"]:
        if field not in registry:
            raise ValueError(f"customer QA workflow registry missing top-level field: {field}")
    if not isinstance(registry["scenes"], dict) or not registry["scenes"]:
        raise ValueError("customer QA workflow registry scenes must be a non-empty object")
    if registry["default_intent"] not in registry["scenes"]:
        raise ValueError("customer QA workflow default_intent must exist in scenes")
    for intent, scene in registry["scenes"].items():
        for field in schema["required_scene_fields"]:
            if field not in scene:
                raise ValueError(f"customer QA scene={intent} missing field: {field}")
        if not isinstance(scene["steps"], list) or not scene["steps"]:
            raise ValueError(f"customer QA scene={intent} steps must be non-empty")
        for step in scene["steps"]:
            _validate_step(intent, step, schema)


def _validate_step(intent: str, step: Dict[str, Any], schema: Dict[str, Any]) -> None:
    for field in schema["required_step_fields"]:
        if field not in step:
            raise ValueError(f"customer QA scene={intent} step missing field: {field}")
    if step["type"] not in schema["allowed_step_types"]:
        raise ValueError(f"customer QA scene={intent} step={step['step_id']} has invalid type={step['type']}")
    if step["type"] == "tool_call":
        for field in schema["required_tool_step_fields"]:
            if field not in step:
                raise ValueError(f"customer QA scene={intent} tool step={step['step_id']} missing field: {field}")


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

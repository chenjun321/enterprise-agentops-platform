from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    ok: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, payload: Dict[str, Any]) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def names(self):
        return sorted(self._tools.keys())


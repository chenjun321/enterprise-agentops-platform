import ast
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolResult


class CodeSearchTool(BaseTool):
    name = "CodeSearchTool"
    description = "Search source code by keyword and extract related Python symbols."

    def __init__(self, repo_path: str = "data/demo_code"):
        self.repo_path = Path(repo_path)

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        query = payload.get("query") or payload.get("keyword") or ""
        keywords = payload.get("trace_keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        if query:
            keywords = [query] + keywords

        matches = []
        for keyword in keywords[:5]:
            matches.extend(self._rg(keyword))

        unique = {}
        for match in matches:
            key = (match["file"], match["line"])
            unique[key] = match

        related = []
        for match in list(unique.values())[:8]:
            symbol = self._nearest_symbol(Path(match["file"]), match["line"])
            related.append(
                {
                    "file": match["file"],
                    "line": match["line"],
                    "function": symbol,
                    "reason": f"matched keyword near symbol {symbol or 'module'}",
                    "code_snippet": match["text"],
                }
            )

        return ToolResult(ok=True, data={"matches": related})

    def _rg(self, keyword: str) -> List[Dict[str, Any]]:
        if not keyword:
            return []
        try:
            completed = subprocess.run(
                ["rg", "--line-number", "--no-heading", keyword, str(self.repo_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return self._fallback_search(keyword)

        results = []
        for line in completed.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3:
                file_name, line_no, text = parts
                results.append({"file": file_name, "line": int(line_no), "text": text.strip()})
        return results

    def _fallback_search(self, keyword: str) -> List[Dict[str, Any]]:
        results = []
        for path in self.repo_path.rglob("*.py"):
            for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if keyword.lower() in line.lower():
                    results.append({"file": str(path), "line": idx, "text": line.strip()})
        return results

    def _nearest_symbol(self, path: Path, line_no: int) -> Optional[str]:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception:
            return None

        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = getattr(node, "lineno", 0)
                end = getattr(node, "end_lineno", start)
                if start <= line_no <= end:
                    candidates.append((start, node.name))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]


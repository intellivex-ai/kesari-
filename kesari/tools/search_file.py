"""
Kesari AI — Search File Tool
Searches for files on the user's system.
"""
import os
import time
from pathlib import Path
from kesari.tools.base_tool import BaseTool


class SearchFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_file"

    @property
    def description(self) -> str:
        return (
            "Search for files on the user's PC by name or pattern. "
            "Searches common directories (Desktop, Documents, Downloads, etc.). "
            "Can use wildcards like *.pdf, *.py. Returns file paths with sizes."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "File name or glob pattern to search for (e.g. 'resume.pdf', '*.py', 'project*')",
                },
                "directory": {
                    "type": "string",
                    "description": "Optional specific directory to search in. If not provided, searches common folders.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        query: str,
        directory: str = "",
        max_results: int = 10,
    ) -> dict:
        home = Path.home()
        search_dirs = []

        if directory:
            search_dirs = [Path(directory)]
        else:
            # Search common user directories
            search_dirs = [
                home / "Desktop",
                home / "Documents",
                home / "Downloads",
                home / "Pictures",
                home / "Videos",
                home / "Music",
                home,
            ]

        results = []
        seen_paths = set()
        pattern = query if "*" in query or "?" in query else f"*{query}*"

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                for match in search_dir.rglob(pattern):
                    if len(results) >= max_results:
                        break
                    match_path = str(match.resolve())
                    if match_path in seen_paths:
                        continue
                    seen_paths.add(match_path)
                    try:
                        stat = match.stat()
                        results.append({
                            "path": str(match),
                            "name": match.name,
                            "size_bytes": stat.st_size,
                            "size_human": self._human_size(stat.st_size),
                            "modified": time.strftime(
                                "%Y-%m-%d %H:%M",
                                time.localtime(stat.st_mtime),
                            ),
                            "is_dir": match.is_dir(),
                        })
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue

            if len(results) >= max_results:
                break

        if results:
            return {
                "status": "success",
                "count": len(results),
                "files": results,
            }
        return {
            "status": "not_found",
            "message": f"No files matching '{query}' found.",
        }

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

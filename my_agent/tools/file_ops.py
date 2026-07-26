import os
import re
from pathlib import Path
from my_agent.tools.registry import Tool

HOME = Path.home()
CWD = Path.cwd()
ALLOWED_PREFIXES = [HOME, CWD]


class FileOpsTool(Tool):
    name = "file_ops"
    description = "Read, write, list, search, or delete files. Can also search file contents with regex (grep). Safe by default - operations outside the home directory are blocked."
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "list", "delete", "grep"],
                "description": "read: view file contents; write: create/overwrite a file; list: show directory contents; delete: remove file or empty directory; grep: search file contents with regex",
            },
            "path": {
                "type": "string",
                "description": "File or directory path. Only paths under your home directory and current directory are allowed.",
            },
            "content": {
                "type": "string",
                "description": "Content to write (only for 'write' operation), or regex pattern (only for 'grep' operation)",
            },
        },
        "required": ["operation", "path"],
    }

    def execute(self, operation: str, path: str, content: str = "") -> str:
        path_obj = Path(path).expanduser().resolve()
        if not self._is_allowed(path_obj):
            return f"Access denied: '{path}' is outside allowed directories.\nAllowed: {ALLOWED_PREFIXES[0]}, {ALLOWED_PREFIXES[1]}"

        if operation == "read":
            return self._read(path_obj)
        elif operation == "write":
            return self._write(path_obj, content)
        elif operation == "list":
            return self._list(path_obj)
        elif operation == "delete":
            return self._delete(path_obj)
        elif operation == "grep":
            return self._grep(path_obj, content)
        return f"Unknown operation: {operation}"

    def _is_allowed(self, path: Path) -> bool:
        for prefix in ALLOWED_PREFIXES:
            if prefix in path.parents or path == prefix:
                return True
        return False

    def _read(self, path: Path) -> str:
        if not path.exists():
            return f"File not found: {path}"
        if path.is_dir():
            return self._list(path)
        try:
            data = path.read_bytes()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Binary file: {path.name}, {len(data)} bytes. Cannot display as text.]"
        except Exception as e:
            return f"Error reading file: {e}"

    def _write(self, path: Path, content: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"

    def _list(self, path: Path) -> str:
        if not path.exists():
            return f"Path not found: {path}"
        items = list(path.iterdir())
        result = [f"Contents of {path} ({len(items)} items):"]
        for item in sorted(items):
            if item.is_file():
                size = item.stat().st_size
                size_str = f" ({self._format_size(size)})" if size > 0 else ""
                result.append(f"  \uD83D\uDCC4 {item.name}{size_str}")
            else:
                result.append(f"  \uD83D\uDCC1 {item.name}/")
        return "\n".join(result)

    def _delete(self, path: Path) -> str:
        if not path.exists():
            return f"Path not found: {path}"
        if path.is_file():
            path.unlink()
            return f"Deleted file: {path}"
        import shutil
        shutil.rmtree(path)
        return f"Deleted directory: {path}"

    def _grep(self, path: Path, pattern: str) -> str:
        if not path.is_dir():
            return f"grep requires a directory path, not a file: {path}"
        if not pattern:
            return "No search pattern provided."
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Invalid regex pattern: {e}"
        matches = []
        max_files = 50
        for f in path.rglob("*"):
            if not f.is_file():
                continue
            if len(matches) >= max_files * 20:
                break
            try:
                if f.stat().st_size > 1024 * 1024:
                    continue
                text = f.read_bytes()
                try:
                    text = text.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = f.relative_to(path)
                        matches.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                        if len(matches) >= 100:
                            break
            except Exception:
                continue
        if not matches:
            return f"No matches found for '{pattern}' in {path}"
        result = [f"Found {len(matches)} match(es) for '{pattern}' in {path}:"]
        result.extend(matches)
        if len(matches) >= 100:
            result.append("... (results truncated)")
        return "\n".join(result)

    @staticmethod
    def _format_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"
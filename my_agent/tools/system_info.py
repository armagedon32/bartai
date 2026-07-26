import platform
import os
from datetime import datetime
from my_agent.tools.registry import Tool


class SystemInfoTool(Tool):
    name = "system_info"
    description = "Get information about the user's computer system: OS, CPU, memory, disk, Python version, and current working directory. Use this when the user asks about their system or environment."
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "os", "hardware", "disk", "python", "process"],
                "description": "Category of information to retrieve. 'all' returns everything.",
            },
        },
        "required": ["category"],
    }

    def execute(self, category: str = "all") -> str:
        parts = []
        if category in ("all", "os"):
            parts.append(self._get_os_info())
        if category in ("all", "hardware"):
            parts.append(self._get_hardware_info())
        if category in ("all", "disk"):
            parts.append(self._get_disk_info())
        if category in ("all", "python"):
            parts.append(self._get_python_info())
        if category in ("all", "process"):
            parts.append(self._get_process_info())
        return "\n\n".join(parts)

    def _get_os_info(self) -> str:
        lines = ["--- System / OS ---"]
        lines.append(f"System: {platform.system()} {platform.release()}")
        lines.append(f"Version: {platform.version()}")
        lines.append(f"Machine: {platform.machine()}")
        lines.append(f"Node: {platform.node()}")
        return "\n".join(lines)

    def _get_hardware_info(self) -> str:
        lines = ["--- Hardware ---"]
        lines.append(f"Processor: {platform.processor() or 'unknown'}")
        lines.append(f"CPU count: {os.cpu_count() or 'unknown'}")
        try:
            import psutil
            mem = psutil.virtual_memory()
            lines.append(f"RAM: {self._fmt(mem.total)} total, {self._fmt(mem.available)} available")
        except ImportError:
            pass
        return "\n".join(lines)

    def _get_disk_info(self) -> str:
        lines = ["--- Disk ---"]
        try:
            import shutil
            usage = shutil.disk_usage(os.getcwd())
            lines.append(f"Current disk ({os.getcwd()[:2]}):")
            lines.append(f"  Total: {self._fmt(usage.total)}")
            lines.append(f"  Used:  {self._fmt(usage.used)}")
            lines.append(f"  Free:  {self._fmt(usage.free)}")
        except Exception:
            lines.append("(disk info unavailable)")
        return "\n".join(lines)

    def _get_python_info(self) -> str:
        lines = ["--- Python ---"]
        lines.append(f"Version: {platform.python_version()}")
        lines.append(f"Executable: {__import__('sys').executable}")
        lines.append(f"CWD: {os.getcwd()}")
        return "\n".join(lines)

    def _get_process_info(self) -> str:
        import time
        lines = ["--- Process ---"]
        lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"PID: {os.getpid()}")
        return "\n".join(lines)

    @staticmethod
    def _fmt(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}PB"
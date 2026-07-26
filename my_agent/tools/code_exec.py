import subprocess
import sys
import tempfile
import os
import io
import contextlib
import textwrap
from pathlib import Path
from my_agent.tools.registry import Tool

SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'ascii': ascii, 'bin': bin, 'bool': bool,
    'bytearray': bytearray, 'bytes': bytes, 'callable': callable, 'chr': chr,
    'complex': complex, 'dict': dict, 'dir': dir, 'divmod': divmod, 'enumerate': enumerate,
    'eval': None, 'exec': None, 'filter': filter, 'float': float, 'format': format,
    'frozenset': frozenset, 'getattr': getattr, 'globals': None, 'hasattr': hasattr,
    'hash': hash, 'hex': hex, 'id': id, 'input': None, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list, 'locals': None,
    'map': map, 'max': max, 'min': min, 'next': next, 'object': object, 'oct': oct,
    'open': None, 'ord': ord, 'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
    'str': str, 'sum': sum, 'super': super, 'tuple': tuple, 'type': type, 'vars': None,
    'zip': zip, '__import__': None,
    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    'KeyError': KeyError, 'IndexError': IndexError, 'StopIteration': StopIteration,
    'RuntimeError': RuntimeError, 'ZeroDivisionError': ZeroDivisionError,
    'True': True, 'False': False, 'None': None,
}


class CodeExecTool(Tool):
    name = "execute_code"
    description = "Execute Python code or shell commands. Use for data analysis, calculations, file processing, automation, and running scripts. Python has access to common libraries (json, re, math, random, datetime, pathlib, collections, itertools). Shell commands run with 30s timeout."
    parameters = {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": ["python", "shell"],
                "description": "Language to execute",
            },
            "code": {
                "type": "string",
                "description": "The code or command to execute",
            },
        },
        "required": ["language", "code"],
    }

    def execute(self, language: str, code: str) -> str:
        if language == "python":
            return self._exec_python(code)
        elif language == "shell":
            return self._exec_shell(code)
        return f"Unsupported language: {language}"

    def _exec_python(self, code: str) -> str:
        try:
            stdout = io.StringIO()
            stderr = io.StringIO()
            safe_globals = {"__builtins__": SAFE_BUILTINS}
            safe_globals["__name__"] = "__main__"
            imports = [
                "json", "re", "math", "random", "datetime", "pathlib", "collections",
                "itertools", "statistics", "typing", "os", "sys",
            ]
            for mod_name in imports:
                try:
                    safe_globals[mod_name.split('.')[0]] = __import__(mod_name)
                except ImportError:
                    pass
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(code, safe_globals)
            out = stdout.getvalue()
            err = stderr.getvalue()
            result = ""
            if out:
                result += f"--- stdout ---\n{out}"
            if err:
                result += f"--- stderr ---\n{err}"
            return result or "Code executed successfully (no output)."
        except Exception as e:
            return f"Python execution error:\n{type(e).__name__}: {e}"

    def _exec_shell(self, code: str) -> str:
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = ""
            if result.stdout:
                output += f"--- stdout ---\n{result.stdout}"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr}"
            output += f"\n--- exit code: {result.returncode} ---"
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Shell execution error: {e}"


class InstallPackageTool(Tool):
    name = "install_package"
    description = "Install Python packages using pip. Use when the user needs a library that isn't available. Packages are installed in the current environment."
    parameters = {
        "type": "object",
        "properties": {
            "packages": {
                "type": "string",
                "description": "Package name(s) to install, space-separated (e.g. 'pandas numpy')",
            },
        },
        "required": ["packages"],
    }

    def execute(self, packages: str) -> str:
        try:
            result = subprocess.run(
                f"{sys.executable} -m pip install {packages}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = ""
            if result.stdout:
                output += f"--- stdout ---\n{result.stdout}"
            if result.stderr:
                output += f"--- stderr ---\n{result.stderr}"
            output += f"\n--- exit code: {result.returncode} ---"
            return output
        except subprocess.TimeoutExpired:
            return "Package installation timed out after 120 seconds."
        except Exception as e:
            return f"Installation error: {e}"

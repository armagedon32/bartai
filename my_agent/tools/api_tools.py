import requests
import json
from my_agent.tools.registry import Tool


class APITool(Tool):
    name = "call_api"
    description = "Make HTTP requests to external APIs. Supports GET, POST, PUT, DELETE with custom headers and body."
    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP method",
            },
            "url": {
                "type": "string",
                "description": "Request URL",
            },
            "headers": {
                "type": "string",
                "description": "Optional JSON object string of headers to send",
            },
            "body": {
                "type": "string",
                "description": "Optional JSON body string for POST/PUT requests",
            },
        },
        "required": ["method", "url"],
    }

    def execute(self, method: str, url: str, headers: str = "{}", body: str = "") -> str:
        try:
            hdrs = json.loads(headers) if isinstance(headers, str) else headers
            data = json.loads(body) if body else None
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=hdrs,
                json=data,
                timeout=30,
            )
            result = f"Status: {resp.status_code}\n"
            try:
                body_text = json.dumps(resp.json(), indent=2)
            except Exception:
                body_text = resp.text[:5000]
            result += f"Body:\n{body_text}"
            return result
        except Exception as e:
            return f"API call failed: {e}"

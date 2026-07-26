import base64
import uuid
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
from my_agent.tools.registry import Tool

# Load env from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))


class GenerateImageTool(Tool):
    name = "generate_image"
    description = "Generate an image from a text description using AI. Requires OpenRouter credits (~$0.04-0.10 per image). Use this when the user asks you to create, draw, or generate an image. The image is saved and displayed in the chat."
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed description of the image to generate. Be specific about style, colors, composition, and mood.",
            },
            "model": {
                "type": "string",
                "enum": ["bytedance-seed/seedream-4.5", "google/gemini-3.1-flash-image", "black-forest-labs/flux.2-pro"],
                "description": "Model to use. seedream-4.5 is cheapest ($0.04/image). gemini-3.1-flash-image is fast. flux.2-pro is highest quality.",
            },
            "resolution": {
                "type": "string",
                "enum": ["1K", "2K", "4K"],
                "description": "Resolution tier. 1K = 1024px, 2K = 2048px.",
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"],
                "description": "Aspect ratio of the output image. Default is 1:1 (square).",
            },
        },
        "required": ["prompt"],
    }

    def execute(self, prompt: str, model: str = "bytedance-seed/seedream-4.5", resolution: str = "1K", aspect_ratio: str = "1:1") -> str:
        try:
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            if not api_key:
                return "Image generation is not configured (missing API key)."
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
            }
            resp = requests.post(
                f"{base_url}/images",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code != 200:
                return f"Image generation failed (HTTP {resp.status_code}): {resp.text[:500]}"

            data = resp.json()
            if "data" not in data or not data["data"]:
                return f"Image generation returned no data: {resp.text[:300]}"

            img_data = data["data"][0]
            cost = data.get("usage", {}).get("cost", "unknown")

            upload_dir = Path(__file__).parent.parent / "web" / "static" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)

            if "b64_json" in img_data:
                raw = img_data["b64_json"]
                if "," in raw:
                    raw = raw.split(",")[1]
                ext = "png"
                name = f"gen_{uuid.uuid4().hex}.{ext}"
                path = upload_dir / name
                path.write_bytes(base64.b64decode(raw))
                url = f"/uploads/{name}"
                return f"![{prompt}]({url})\n\n**Prompt:** {prompt}\n**Model:** {model}\n**Cost:** ${cost}"
            elif "url" in img_data:
                url = img_data["url"]
                try:
                    img_resp = requests.get(url, timeout=30)
                    if img_resp.status_code == 200:
                        ext = "png"
                        name = f"gen_{uuid.uuid4().hex}.{ext}"
                        path = upload_dir / name
                        path.write_bytes(img_resp.content)
                        local_url = f"/uploads/{name}"
                        return f"![{prompt}]({local_url})\n\n**Prompt:** {prompt}\n**Model:** {model}\n**Cost:** ${cost}"
                except Exception:
                    pass
                return f"Image generated: {url}\n\n**Prompt:** {prompt}\n**Model:** {model}"
            else:
                return f"Unexpected response format: {str(img_data)[:300]}"

        except requests.Timeout:
            return "Image generation timed out after 60 seconds."
        except Exception as e:
            return f"Image generation error: {e}"
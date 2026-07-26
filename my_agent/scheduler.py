import json
import threading
import time
from datetime import datetime
from pathlib import Path


class TaskScheduler:
    def __init__(self, tasks_file: str, agent):
        self.tasks_file = Path(tasks_file)
        self.agent = agent
        self.tasks: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._load()

    def _load(self):
        try:
            with open(self.tasks_file) as f:
                self.tasks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.tasks = []

    def _save(self):
        with open(self.tasks_file, "w") as f:
            json.dump(self.tasks, f, indent=2)

    def add_task(self, name: str, prompt: str, interval_hours: int):
        self.tasks.append({
            "name": name,
            "prompt": prompt,
            "interval_hours": interval_hours,
            "last_run": None,
            "next_run": time.time() + interval_hours * 3600,
        })
        self._save()
        return f"Task '{name}' scheduled every {interval_hours}h"

    def list_tasks(self) -> str:
        if not self.tasks:
            return "No scheduled tasks."
        lines = ["Scheduled tasks:"]
        now = time.time()
        for t in self.tasks:
            next_time = datetime.fromtimestamp(t["next_run"]).strftime("%Y-%m-%d %H:%M")
            last = t.get("last_run")
            last_str = datetime.fromtimestamp(last).strftime("%Y-%m-%d %H:%M") if last else "never"
            lines.append(f"  - {t['name']}: next={next_time}, last={last_str}")
        return "\n".join(lines)

    def remove_task(self, name: str) -> str:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["name"] != name]
        if len(self.tasks) < before:
            self._save()
            return f"Removed task '{name}'"
        return f"Task '{name}' not found"

    def _run_loop(self):
        while self._running:
            now = time.time()
            for task in self.tasks:
                if now >= task["next_run"]:
                    try:
                        result = self.agent.run_task(task["prompt"])
                        task["last_run"] = now
                        task["next_run"] = now + task["interval_hours"] * 3600
                        self._save()
                        print(f"[Scheduler] Ran '{task['name']}': {result[:200]}")
                    except Exception as e:
                        print(f"[Scheduler] Task '{task['name']}' failed: {e}")
            time.sleep(30)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

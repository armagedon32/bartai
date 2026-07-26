import sys
import shutil
import tempfile
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.table import Table
from rich import box

from my_agent.config import Config
from my_agent.agent import Agent

console = Console()


def print_header(text: str, style: str = "bold cyan"):
    console.print(Panel.fit(text, border_style="cyan"))


def print_error(text: str):
    console.print(Panel(text, border_style="red"))


def print_info(text: str):
    console.print(f"[dim]{text}[/dim]")


def print_markdown(text: str):
    try:
        console.print(Panel(Markdown(text), border_style="green"))
    except Exception:
        console.print(Panel(text, border_style="green"))


def get_multiline_input() -> str:
    console.print("[dim]Enter message (Esc+Enter to send, Ctrl+C to cancel):[/dim]")
    lines = []
    try:
        while True:
            line = input()
            if line == "\x1b":  # Escape key
                break
            lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
    text = "\n".join(lines)
    return text.strip()


def check_config(config: Config):
    if not config.openrouter_api_key:
        print_error(
            "OPENROUTER_API_KEY not set!\n\n"
            "1. Copy .env.example to .env\n"
            "2. Edit .env and add your OpenRouter API key\n"
            "3. Get a key at: https://openrouter.ai/keys"
        )
        return False
    if config.openrouter_api_key == "your_openrouter_api_key_here":
        print_error("Please set your real OpenRouter API key in the .env file.")
        return False
    return True


def main():
    config = Config()
    agent = Agent(config)

    print_header(
        "[bold]BArt AI[/bold]\n"
        "Streaming responses · Multi-conversation · RAG memory · Tools\n"
        "Type /help for commands, /exit to quit"
    )

    if not check_config(config):
        return

    agent.scheduler.start()

    # Show current conversation
    conv = agent.conversations.current
    print_info(f"Active conversation: [bold]{conv}[/bold]")

    try:
        while True:
            try:
                user_input = input("\n[bold yellow]You[/bold yellow] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                if user_input.startswith("//"):
                    user_input = user_input[1:]
                else:
                    cmd_result = agent.handle_command(user_input)
                    if cmd_result == "__EXIT__":
                        break
                    if cmd_result is not None:
                        print_info(cmd_result)
                    continue

            # Show a spinner while waiting for the first token
            spinner = Spinner("dots", text="Thinking...")
            response_text = ""
            tool_results = []
            usage_info = None

            with Live(spinner, refresh_per_second=10, console=console) as live:
                for event in agent.chat_stream(user_input):
                    if event["type"] == "token":
                        response_text += event["content"]
                        if response_text:
                            try:
                                live.update(Markdown(response_text))
                            except Exception:
                                live.update(Text(response_text))
                        else:
                            live.update(spinner)

                    elif event["type"] == "tool_calls":
                        live.update(Spinner("dots", text="Using tools..."))
                        for tc in event["tool_calls"]:
                            tool_results.append(tc["function"]["name"])

                    elif event["type"] == "tool_result":
                        pass

                    elif event["type"] == "usage":
                        usage_info = event["usage"]

                    elif event["type"] == "error":
                        live.stop()
                        print_error(event["content"])
                        response_text = ""

                    elif event["type"] == "done":
                        response_text = event["content"]
                        live.stop()

            if response_text:
                print_markdown(response_text)

            if tool_results:
                tools_str = ", ".join(f"[bold]{t}[/bold]" for t in set(tool_results))
                print_info(f"Tools used: {tools_str}")

            if usage_info:
                print_info(
                    f"Tokens: {usage_info['prompt_tokens']}→{usage_info['completion_tokens']} "
                    f"(total: {usage_info['total_tokens']})"
                )

    finally:
        agent.scheduler.stop()
        print_info("\nGoodbye!")

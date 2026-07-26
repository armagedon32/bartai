import base64
import uuid
import io
from pathlib import Path
from my_agent.tools.registry import Tool


class CreateChartTool(Tool):
    name = "create_chart"
    description = "Create a chart or data visualization (bar, line, pie, scatter, histogram) from data. This is free and works without API credits. The chart image is saved and displayed in the chat."
    parameters = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line", "pie", "scatter", "histogram", "horizontal_bar"],
                "description": "Type of chart to create.",
            },
            "title": {
                "type": "string",
                "description": "Title of the chart.",
            },
            "labels": {
                "type": "string",
                "description": "Comma-separated labels for the data points (e.g. 'Q1,Q2,Q3,Q4' or 'Apples,Oranges,Bananas'). For histogram, this is the x-axis label.",
            },
            "values": {
                "type": "string",
                "description": "Comma-separated numeric values (e.g. '10,25,15,30').",
            },
            "xlabel": {
                "type": "string",
                "description": "Label for the x-axis.",
            },
            "ylabel": {
                "type": "string",
                "description": "Label for the y-axis.",
            },
        },
        "required": ["chart_type", "title", "labels", "values"],
    }

    def execute(self, chart_type: str, title: str, labels: str, values: str,
                xlabel: str = "", ylabel: str = "") -> str:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            parsed_labels = [l.strip() for l in labels.split(",")]
            parsed_values = [float(v.strip()) for v in values.split(",")]

            fig, ax = plt.subplots(figsize=(8, 5))
            fig.patch.set_facecolor("#1a1a1a")
            ax.set_facecolor("#2a2a2a")
            ax.tick_params(colors="#e0e0e0")
            ax.spines["bottom"].set_color("#444")
            ax.spines["left"].set_color("#444")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_title(title, color="#e0e0e0", fontsize=14, fontweight="bold")
            if xlabel:
                ax.set_xlabel(xlabel, color="#a0a0a0")
            if ylabel:
                ax.set_ylabel(ylabel, color="#a0a0a0")

            colors = ["#10a37f", "#1a8fe0", "#e0a010", "#e06040", "#9060e0",
                      "#20b0b0", "#d060a0", "#60a030", "#e08030", "#4080c0"]

            if chart_type == "bar":
                bars = ax.bar(parsed_labels, parsed_values, color=colors[:len(parsed_labels)], edgecolor="none")
                for bar, v in zip(bars, parsed_values):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            f"{v}", ha="center", va="bottom", color="#e0e0e0", fontsize=10)

            elif chart_type == "horizontal_bar":
                bars = ax.barh(parsed_labels, parsed_values, color=colors[:len(parsed_labels)], edgecolor="none")
                for bar, v in zip(bars, parsed_values):
                    ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                            f"{v}", ha="left", va="center", color="#e0e0e0", fontsize=10)

            elif chart_type == "line":
                ax.plot(parsed_labels, parsed_values, marker="o", color="#10a37f",
                        linewidth=2, markersize=6, markerfacecolor="#10a37f")
                for i, v in enumerate(parsed_values):
                    ax.text(i, v, f"{v}", ha="center", va="bottom", color="#e0e0e0", fontsize=10)

            elif chart_type == "pie":
                wedges, texts, autotexts = ax.pie(
                    parsed_values, labels=parsed_labels, autopct="%1.1f%%",
                    colors=colors[:len(parsed_labels)], startangle=90,
                    textprops={"color": "#e0e0e0", "fontsize": 10},
                )
                for at in autotexts:
                    at.set_color("white")

            elif chart_type == "scatter":
                x = list(range(len(parsed_values)))
                ax.scatter(x, parsed_values, color="#10a37f", s=60, zorder=3)
                ax.plot(x, parsed_values, color="#10a37f", alpha=0.3, linewidth=1)
                ax.set_xticks(x)
                ax.set_xticklabels(parsed_labels)
                for i, v in enumerate(parsed_values):
                    ax.text(i, v, f"{v}", ha="center", va="bottom", color="#e0e0e0", fontsize=10)

            elif chart_type == "histogram":
                ax.hist(parsed_values, bins=min(10, len(parsed_values)),
                        color="#10a37f", edgecolor="#2a2a2a", alpha=0.8)
                ax.set_xlabel(parsed_labels[0] if parsed_labels else "Value")

            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                        facecolor="#1a1a1a", edgecolor="none")
            plt.close(fig)
            buf.seek(0)

            upload_dir = Path(__file__).parent.parent / "web" / "static" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            name = f"chart_{uuid.uuid4().hex}.png"
            path = upload_dir / name
            path.write_bytes(buf.getvalue())
            url = f"/uploads/{name}"

            return f"![{title}]({url})\n\n**Chart:** {title}\n**Type:** {chart_type}\n**Data:** {labels} = {values}"

        except ImportError:
            return "Chart creation requires matplotlib. Install it with: pip install matplotlib"
        except Exception as e:
            return f"Chart creation error: {e}"
import uuid
import io
from pathlib import Path
from my_agent.tools.registry import Tool


class CreateTableTool(Tool):
    name = "create_table"
    description = "Create a beautiful graphical table rendered as an image. Supports multiple columns, headers, row data, optional summary row (sum/average/count), and cell highlighting. The table image is saved and displayed in the chat. Use this for presenting data in a clean, professional format."
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title displayed above the table.",
            },
            "headers": {
                "type": "string",
                "description": "Comma-separated column headers (e.g. 'Name,Age,Score').",
            },
            "rows": {
                "type": "string",
                "description": "Rows of data. Each row is pipe-separated, rows are semicolon-separated (e.g. 'Alice|25|92;Bob|30|85;Charlie|22|78').",
            },
            "summary": {
                "type": "string",
                "enum": ["none", "sum", "average", "count"],
                "description": "Optional summary row at the bottom.",
            },
            "highlight_col": {
                "type": "string",
                "description": "Column name (from headers) to highlight with a color gradient based on values.",
            },
        },
        "required": ["title", "headers", "rows"],
    }

    def execute(self, title: str, headers: str, rows: str,
                summary: str = "none", highlight_col: str = "") -> str:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np

            parsed_headers = [h.strip() for h in headers.split(",")]
            parsed_rows = []
            for row_str in rows.split(";"):
                row_str = row_str.strip()
                if row_str:
                    parsed_rows.append([c.strip() for c in row_str.split("|")])

            n_cols = len(parsed_headers)
            n_rows = len(parsed_rows)

            if n_rows == 0:
                return "No data rows provided."

            cell_text = [parsed_headers] + parsed_rows
            highlight_idx = -1
            if highlight_col:
                for i, h in enumerate(parsed_headers):
                    if h.lower() == highlight_col.lower():
                        highlight_idx = i
                        break

            if summary != "none":
                summary_row = [""] * n_cols
                try:
                    numeric_cols = []
                    for ci in range(n_cols):
                        vals = []
                        for r in parsed_rows:
                            if ci < len(r):
                                try:
                                    vals.append(float(r[ci]))
                                except ValueError:
                                    pass
                        if vals:
                            numeric_cols.append((ci, vals))

                    if numeric_cols:
                        if summary == "sum":
                            for ci, vals in numeric_cols:
                                summary_row[ci] = str(sum(vals))
                            summary_row[0] = "Sum"
                        elif summary == "average":
                            for ci, vals in numeric_cols:
                                summary_row[ci] = f"{sum(vals)/len(vals):.2f}"
                            summary_row[0] = "Average"
                        elif summary == "count":
                            for ci, vals in numeric_cols:
                                summary_row[ci] = str(len(vals))
                            summary_row[0] = "Count"
                except Exception:
                    pass
                cell_text.append(summary_row)

            fig_height = max(2.0, 0.5 + len(cell_text) * 0.55)
            fig, ax = plt.subplots(figsize=(min(12, n_cols * 2.2 + 1), fig_height))
            fig.patch.set_facecolor("#1a1a1a")
            ax.axis("off")

            col_widths = [0.15] + [1.0 / n_cols] * n_cols
            table = ax.table(
                cellText=cell_text,
                colLabels=None,
                loc="center",
                cellLoc="center",
                colWidths=[1.0 / n_cols] * n_cols,
            )
            table.auto_set_font_size(False)
            font_size = min(13, max(8, int(180 / len(cell_text))))
            table.set_fontsize(font_size)
            table.scale(1, 1.6)

            header_color = "#10a37f"
            alt_color = "#2a2a2a"
            base_color = "#222222"
            accent_color = "#1e3a3a"

            for i in range(len(cell_text)):
                for j in range(n_cols):
                    cell = table[i, j]
                    cell.set_edgecolor("#444444")
                    cell.set_linewidth(0.5)
                    cell.set_height(0.12)

                    if i == 0:
                        cell.set_facecolor(header_color)
                        cell.set_text_props(color="white", fontweight="bold", fontsize=font_size + 1)
                    elif i == len(cell_text) - 1 and summary != "none":
                        cell.set_facecolor("#1a3a2a")
                        cell.set_text_props(color="#10a37f", fontweight="bold", fontsize=font_size)
                    elif i % 2 == 0:
                        cell.set_facecolor(alt_color)
                        cell.set_text_props(color="#e0e0e0", fontsize=font_size)
                    else:
                        cell.set_facecolor(base_color)
                        cell.set_text_props(color="#e0e0e0", fontsize=font_size)

            if highlight_idx >= 0:
                vals = []
                for r in parsed_rows:
                    if highlight_idx < len(r):
                        try:
                            vals.append(float(r[highlight_idx]))
                        except ValueError:
                            vals.append(0)
                if vals:
                    vmin, vmax = min(vals), max(vals)
                    rng = vmax - vmin if vmax != vmin else 1
                    for i, r in enumerate(parsed_rows):
                        if highlight_idx < len(r):
                            try:
                                v = float(r[highlight_idx])
                                norm = (v - vmin) / rng
                                r_comp = int(16 + norm * 80)
                                g_comp = int(163 - norm * 60)
                                b_comp = int(127 - norm * 50)
                                cell = table[i + 1, highlight_idx]
                                cell.set_facecolor(f"#{r_comp:02x}{g_comp:02x}{b_comp:02x}")
                                cell.set_text_props(color="white", fontweight="bold")
                            except ValueError:
                                pass

            ax.set_title(title, color="#e0e0e0", fontsize=14, fontweight="bold", pad=16)

            plt.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                        facecolor="#1a1a1a", edgecolor="none")
            plt.close(fig)
            buf.seek(0)

            upload_dir = Path(__file__).parent.parent / "web" / "static" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            name = f"tbl_{uuid.uuid4().hex}.png"
            path = upload_dir / name
            path.write_bytes(buf.getvalue())
            url = f"/uploads/{name}"

            return f"![{title}]({url})\n\n**Table:** {title}\n**Columns:** {', '.join(parsed_headers)}\n**Rows:** {n_rows}"

        except ImportError as e:
            return f"Table creation requires matplotlib: pip install matplotlib ({e})"
        except Exception as e:
            return f"Table creation error: {e}"
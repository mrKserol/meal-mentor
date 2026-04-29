"""PNG chart generation for Telegram / API (no UI logic)."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def macros_bar_chart_png(
    totals: dict[str, Any],
    *,
    title: str = "Нутриенты за период",
) -> bytes:
    """Two panels: total kcal; BJU grams."""
    cal = float(totals.get("calories", 0) or 0)
    p = float(totals.get("protein_g", 0) or totals.get("proteins", 0) or 0)
    f = float(totals.get("fat_g", 0) or totals.get("fats", 0) or 0)
    c = float(totals.get("carbs_g", 0) or totals.get("carbohydrates", 0) or 0)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4), dpi=120)
    fig.suptitle(title)
    ax1.bar(["Ккал"], [cal], color="#2ecc71")
    ax1.set_ylabel("ккал")
    ax2.bar(["Белки", "Жиры", "Углеводы"], [p, f, c], color=["#3498db", "#e67e22", "#9b59b6"])
    ax2.set_ylabel("г")
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def weight_line_chart_png(
    points: list[tuple[date, float]],
    *,
    title: str = "Динамика веса",
) -> bytes:
    """Line chart: date vs weight_kg."""
    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    if not points:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center", transform=ax.transAxes)
    else:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, marker="o", color="#2980b9")
        ax.set_ylabel("кг")
        fig.autofmt_xdate()
    ax.set_title(title)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()

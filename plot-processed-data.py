#!/usr/bin/env python3

import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils import OUT_DIR, load_csv

INPUT_CSV = OUT_DIR / "processed-timeseries.csv"


def title(column):
    return column.removeprefix("class_").replace("_", " ").title()


def save_plot(filename):
    output = OUT_DIR / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"Wrote {output}")


def line_chart(rows, column, filename, chart_title, ylabel):
    times = [float(row["t_sec"]) for row in rows if row[column]]
    values = [float(row[column]) for row in rows if row[column]]

    plt.figure(figsize=(10, 5))
    plt.plot(times, values)
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.title(chart_title)
    plt.grid(True)
    save_plot(filename)


def classification_totals(rows):
    class_columns = [column for column in rows[0] if column.startswith("class_")]
    counts = [sum(float(row[column] or 0) for row in rows) for column in class_columns]

    plt.figure(figsize=(10, 5))
    plt.bar([title(column) for column in class_columns], counts)
    plt.xlabel("Classification Type")
    plt.ylabel("Total Classifications")
    plt.title("Classification Totals")
    plt.grid(True, axis="y")
    save_plot("classification-totals.png")


def main():
    rows = load_csv(INPUT_CSV)

    line_chart(
        rows, "flow_count", "flow-count.png", "Flow Count Over Time", "Active Flows"
    )
    line_chart(
        rows,
        "unoptimised_pps",
        "unoptimised-packet-rate.png",
        "Rate of Unoptimised Packets Over Time",
        "Unoptimised packets/s",
    )
    classification_totals(rows)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import csv
from collections import defaultdict
from datetime import UTC, datetime

from utils import OUT_DIR, load_csv

INGRESS_CSV = OUT_DIR / "ingress.csv"
CLASSIFY_CSV = OUT_DIR / "classify.csv"
ECHO_SERVER_CSV = OUT_DIR / "rpi-2-udp-echo-server.csv"
OUTPUT_CSV = OUT_DIR / "processed-timeseries.csv"

SOURCE_LABELS = {
    "192.168.0.50": "node_1",
    "192.168.0.51": "node_2",
}

INGRESS_COLUMNS = [
    "flow_count",
    "classify_backpressure",
    "ingress_packet_total",
    "ingress_byte_total",
    "ingress_pps",
    "ingress_mbps",
    "unoptimised_pps",
    "unoptimised_mbps",
    "unoptimised_percent",
]


def number(value):
    return float(value or 0)


def clean(value):
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()


def second(row, start_ms):
    return int((number(row["timestamp_unix_ms"]) - start_ms) // 1000)


def timestamp(start_ms, time_second):
    unix_time = (start_ms + time_second * 1000) / 1000
    return (
        datetime.fromtimestamp(unix_time, UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def add(row, column, value):
    row[column] = row.get(column, 0) + value


def main():
    ingress_rows = load_csv(INGRESS_CSV)
    classify_rows = load_csv(CLASSIFY_CSV)
    echo_rows = load_csv(ECHO_SERVER_CSV)

    start_ms = min(
        number(row["timestamp_unix_ms"])
        for rows in (ingress_rows, classify_rows, echo_rows)
        for row in rows
    )

    output_rows = defaultdict(dict)

    for row in ingress_rows:
        interval = number(row["interval_secs"])
        packets = number(row["packet_interval"])
        bytes_ = number(row["byte_interval"])
        unoptimised_packets = number(row["unoptimised_packet_interval"])
        unoptimised_bytes = number(row["unoptimised_byte_interval"])

        output_rows[second(row, start_ms)].update(
            {
                "flow_count": row["flow_count"],
                "classify_backpressure": row["classify_backpressure"],
                "ingress_packet_total": row["packet_total"],
                "ingress_byte_total": row["byte_total"],
                "ingress_pps": f"{packets / interval:.2f}" if interval else 0,
                "ingress_mbps": f"{bytes_ * 8 / interval / 1_000_000:.6f}"
                if interval
                else 0,
                "unoptimised_pps": f"{unoptimised_packets / interval:.2f}"
                if interval
                else 0,
                "unoptimised_mbps": f"{unoptimised_bytes * 8 / interval / 1_000_000:.6f}"
                if interval
                else 0,
                "unoptimised_percent": f"{unoptimised_packets / packets * 100:.2f}"
                if packets
                else 0,
            }
        )

    for row in classify_rows:
        add(
            output_rows[second(row, start_ms)], f"class_{clean(row['traffic_type'])}", 1
        )

    for row in echo_rows:
        source = SOURCE_LABELS.get(row["source_ip"], row["source_ip"])
        prefix = f"echo_{clean(source)}"
        output_row = output_rows[second(row, start_ms)]

        add(output_row, f"{prefix}_mbps", number(row["mbps"]))
        add(output_row, f"{prefix}_pps", number(row["packet_rate"]))
        add(output_row, f"{prefix}_packets", number(row["packet_interval"]))
        add(output_row, f"{prefix}_bytes", number(row["byte_interval"]))

    extra_columns = sorted(
        {
            column
            for row in output_rows.values()
            for column in row
            if column.startswith(("echo_", "class_"))
        }
    )
    fieldnames = ["t_sec", "timestamp_utc", *INGRESS_COLUMNS, *extra_columns]

    with OUTPUT_CSV.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for time_second in sorted(output_rows):
            row = {column: "" for column in fieldnames}
            row.update(output_rows[time_second])
            row["t_sec"] = time_second
            row["timestamp_utc"] = timestamp(start_ms, time_second)

            for column in extra_columns:
                row[column] = row[column] or 0

            writer.writerow(row)

    print(f"Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

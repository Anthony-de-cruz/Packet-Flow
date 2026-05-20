#!/usr/bin/env python3

import csv
import socket
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO


UDP_LISTEN_ADDR = "0.0.0.0", 9000
RECV_SIZE = 2048
LOG_INTERVAL_SECONDS = 1.0
LOG_PATH = Path("out/udp-echo-server.csv")

NODE_NAMES = {
    # "10.45.0.2": "ue1",
}

CSV_COLUMNS = [
    "timestamp_utc",
    "timestamp_unix_ms",
    "interval_secs",
    "node",
    "source_ip",
    "last_source_port",
    "packet_total",
    "byte_total",
    "packet_interval",
    "byte_interval",
    "packet_rate",
    "mbps",
]


@dataclass
class SourceStats:
    packet_total: int = 0
    byte_total: int = 0
    packet_interval: int = 0
    byte_interval: int = 0
    last_source_port: int = 0


def utc_timestamp() -> tuple[str, int]:
    now = datetime.now(UTC)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), int(
        now.timestamp() * 1000
    )


def open_csv_writer(path: Path) -> tuple[TextIO, csv.DictWriter]:
    path.parent.mkdir(parents=True, exist_ok=True)
    file = path.open("a", newline="")
    writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)

    if path.stat().st_size == 0:
        writer.writeheader()
        file.flush()

    return file, writer


def log_source_rates(
    writer: csv.DictWriter,
    source_stats: dict[str, SourceStats],
    interval_secs: float,
) -> None:
    if interval_secs <= 0:
        return

    timestamp, timestamp_ms = utc_timestamp()

    for source_ip, stats in sorted(source_stats.items()):
        if stats.packet_interval == 0:
            continue

        packet_rate = stats.packet_interval / interval_secs
        mbps = stats.byte_interval * 8 / interval_secs / 1_000_000
        writer.writerow(
            {
                "timestamp_utc": timestamp,
                "timestamp_unix_ms": timestamp_ms,
                "interval_secs": f"{interval_secs:.6f}",
                #"node": NODE_NAMES.get(source_ip, source_ip),
                "node": "",
                "source_ip": source_ip,
                "last_source_port": stats.last_source_port,
                "packet_total": stats.packet_total,
                "byte_total": stats.byte_total,
                "packet_interval": stats.packet_interval,
                "byte_interval": stats.byte_interval,
                "packet_rate": f"{packet_rate:.2f}",
                "mbps": f"{mbps:.6f}",
            }
        )

        stats.packet_interval = 0
        stats.byte_interval = 0


def main() -> None:
    log_file, log_writer = open_csv_writer(LOG_PATH)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(UDP_LISTEN_ADDR)
            print(
                f"Listening: {UDP_LISTEN_ADDR[0]}:{UDP_LISTEN_ADDR[1]}, "
                f"logging to {LOG_PATH}..."
            )

            source_stats: dict[str, SourceStats] = defaultdict(SourceStats)
            last_log = time.monotonic()

            while True:
                data, address = sock.recvfrom(RECV_SIZE)
                sock.sendto(data, address)

                source_ip, source_port = address
                stats = source_stats[source_ip]
                packet_size = len(data)
                stats.packet_total += 1
                stats.byte_total += packet_size
                stats.packet_interval += 1
                stats.byte_interval += packet_size
                stats.last_source_port = source_port

                now = time.monotonic()
                # Log on interval.
                if now - last_log >= LOG_INTERVAL_SECONDS:
                    interval_secs = now - last_log
                    log_source_rates(log_writer, source_stats, interval_secs)
                    log_file.flush()
                    last_log = now
    finally:
        log_file.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

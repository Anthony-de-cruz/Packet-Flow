#!/usr/bin/env python3

import csv
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image


UDP_BIND_INTERFACE = "uesimtun0"
UDP_DEST_ADDR = "192.168.0.52", 9000
# UDP_DEST_ADDR = "127.0.0.1", 9000

SAMPLE_TYPE_DIR_PATHS = [
    "../Packet-Classifier/data/test/google-meet",
    "../Packet-Classifier/data/test/instagram",
    "../Packet-Classifier/data/test/tiktok",
    "../Packet-Classifier/data/test/twitter",
    "../Packet-Classifier/data/test/youtube",
]
CHUNK_SIZE = 1200
DELAY_SECONDS = 0.01
ECHO_TIMEOUT_SECONDS = 2.0
SAMPLE_SIZE = (28, 28)
LOG_PATH = Path("out/udp-echo-client-latency.csv")

LOG_COLUMNS = [
    "timestamp_utc",
    "timestamp_unix_ms",
    "packet_number",
    "status",
    "latency_ms",
    "reply_ip",
    "reply_port",
    "timeouts",
    "mismatches",
]


def timestamp() -> tuple[str, int]:
    now = datetime.now(UTC)
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z"), int(
        now.timestamp() * 1000
    )


def open_log() -> tuple[object, csv.DictWriter]:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file = LOG_PATH.open("a", newline="")
    writer = csv.DictWriter(file, fieldnames=LOG_COLUMNS)
    if LOG_PATH.stat().st_size == 0:
        writer.writeheader()
    return file, writer


def write_log(
    writer: csv.DictWriter,
    packet_number: int,
    status: str,
    latency_ms: float | None,
    reply_address: tuple[str, int] | None,
    total_timeouts: int,
    total_mismatches: int,
) -> None:
    time_text, time_ms = timestamp()
    writer.writerow(
        {
            "timestamp_utc": time_text,
            "timestamp_unix_ms": time_ms,
            "packet_number": packet_number,
            "status": status,
            "latency_ms": f"{latency_ms:.3f}" if latency_ms is not None else "",
            "reply_ip": reply_address[0] if reply_address else "",
            "reply_port": reply_address[1] if reply_address else "",
            "timeouts": total_timeouts,
            "mismatches": total_mismatches,
        }
    )


def extract_samples(sample_type_dirs: list[str]) -> list[list[bytes]]:
    # Find all samples.
    sample_set_paths: list[list[str]] = []
    for dir in sample_type_dirs:
        sample_set_paths.append(
            sorted(
                str(child)
                for child in Path(dir).iterdir()
                if child.is_file() and child.suffix == ".png"
            )[:50]
        )

    # Extract and preprocess each sample.
    sample_bytes: list[list[bytes]] = []
    for sample_dir in sample_set_paths:
        sample_type_bytes: list[bytes] = []

        for sample_path in sample_dir:
            with Image.open(sample_path) as image:
                sample_type_bytes.append(
                    image.convert("L").resize(SAMPLE_SIZE).tobytes()
                )
        sample_bytes.append(sample_type_bytes)

    return sample_bytes


def main() -> None:
    sample_set = extract_samples(SAMPLE_TYPE_DIR_PATHS)
    total_packets = 0
    total_timeouts = 0
    total_mismatches = 0

    log_file, log_writer = open_log()
    try:
        while True:
            for samples in sample_set:
                print("Opening socket...")
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    print(f"Binding socket to {UDP_BIND_INTERFACE}...")
                    sock.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_BINDTODEVICE,
                        UDP_BIND_INTERFACE.encode() + b"\0",
                    )
                    sock.settimeout(ECHO_TIMEOUT_SECONDS)
                    for sample in samples:
                        start_time = time.perf_counter()
                        sock.sendto(sample, UDP_DEST_ADDR)
                        total_packets += 1
                        try:
                            echo, address = sock.recvfrom(CHUNK_SIZE)
                        except socket.timeout:
                            total_timeouts += 1
                            write_log(
                                log_writer,
                                total_packets,
                                "timeout",
                                None,
                                None,
                                total_timeouts,
                                total_mismatches,
                            )
                            print(
                                f"TX UDP to {UDP_DEST_ADDR[0]}:{UDP_DEST_ADDR[1]}, "
                                f"echo timeout after {ECHO_TIMEOUT_SECONDS:.1f}s, "
                                f"sent={total_packets}, "
                                f"timeouts={total_timeouts}, "
                                f"mismatches={total_mismatches}"
                            )
                        else:
                            round_trip_ms = (time.perf_counter() - start_time) * 1000
                            if echo == sample:
                                write_log(
                                    log_writer,
                                    total_packets,
                                    "ok",
                                    round_trip_ms,
                                    address,
                                    total_timeouts,
                                    total_mismatches,
                                )
                                print(
                                    f"TX/RX UDP via {address[0]}:{address[1]}, "
                                    f"round_trip={round_trip_ms:.2f}ms, "
                                    f"sent={total_packets}, "
                                    f"timeouts={total_timeouts}, "
                                    f"mismatches={total_mismatches}"
                                )
                            else:
                                total_mismatches += 1
                                write_log(
                                    log_writer,
                                    total_packets,
                                    "mismatch",
                                    round_trip_ms,
                                    address,
                                    total_timeouts,
                                    total_mismatches,
                                )
                                print(
                                    f"TX UDP to {UDP_DEST_ADDR[0]}:{UDP_DEST_ADDR[1]}, "
                                    f"echo mismatch from {address[0]}:{address[1]} "
                                    f"after {round_trip_ms:.2f}ms, "
                                    f"sent={total_packets}, "
                                    f"timeouts={total_timeouts}, "
                                    f"mismatches={total_mismatches}"
                                )
                        log_file.flush()
                        time.sleep(DELAY_SECONDS)
    finally:
        log_file.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

#!/usr/bin/env python3

import socket
import time
from pathlib import Path

from PIL import Image


UDP_BIND_INTERFACE = "uesimtun0"
UDP_DEST_ADDR = "192.168.0.52", 9000

SAMPLE_TYPE_DIR_PATHS = [
    "../Packet-Classifier/data/test/google-meet",
    "../Packet-Classifier/data/test/instagram",
    "../Packet-Classifier/data/test/tiktok",
    "../Packet-Classifier/data/test/twitter",
    "../Packet-Classifier/data/test/youtube",
]
CHUNK_SIZE = 1200
DELAY_SECONDS = 0.01
SAMPLE_SIZE = (28, 28)


def extract_samples(sample_type_dirs: list[str]) -> list[list[bytes]]:
    # Find all samples.
    sample_set_paths: list[list[str]] = []
    for dir in sample_type_dirs:
        sample_set_paths.append(sorted(
            str(child) for child in Path(dir).iterdir()
            if child.is_file() and child.suffix == ".png"
        )[:50])

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

    while True:
        for samples in sample_set:
            print("Opening socket...")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                print(f"Binding socket to {UDP_BIND_INTERFACE}...")
                sock.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_BINDTODEVICE,
                    UDP_BIND_INTERFACE.encode() + b"\0")
                for sample in samples:
                    sock.sendto(sample, UDP_DEST_ADDR)
                    total_packets += 1
                    print(
                        f"TX 1 UDP to {UDP_DEST_ADDR[0]}:{UDP_DEST_ADDR[1]}, "
                        f"total packets={total_packets}")
                    time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

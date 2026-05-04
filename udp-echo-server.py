#!/usr/bin/env python3

import socket


UDP_LISTEN_ADDR = "0.0.0.0", 9000


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(UDP_LISTEN_ADDR)
        print(f"Listening: {UDP_LISTEN_ADDR[0]}:{UDP_LISTEN_ADDR[1]}...")

        packet_count = 0

        while True:
            data, address = sock.recvfrom(2048)
            print(
                f"RX/TX UDP via {address[0]}:{address[1]}, "
                f"echoes={packet_count}"
            )
            sock.sendto(data, address)
            packet_count += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

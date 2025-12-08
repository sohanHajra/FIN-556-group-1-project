#!/usr/bin/env python
"""
Convert Databento Nasdaq TotalView-ITCH PCAP (MoldUDP64 UDP packets)
into a "raw ITCH" file that itchfeed.MessageParser can read.

itchfeed expects: 0x00 <1-byte length> <ITCH message bytes> ...
"""

import sys
from scapy.all import PcapReader, UDP  # pip install scapy

def moldudp64_payload_to_itch_frames(payload: bytes) -> list[bytes]:
    """
    Given one MoldUDP64 UDP payload, return a list of framed ITCH messages
    in the format expected by itchfeed: b"\x00<length><msg_bytes>".
    """
    if len(payload) < 20:
        return []

    # MoldUDP64 header
    # 0–9:  session (10 bytes, ASCII)
    # 10–17: sequence number (8 bytes, big-endian)
    # 18–19: message count (2 bytes, big-endian)
    # 20–...: [msg_len(2 bytes), msg_bytes] * count
    session = payload[0:10]  # not used here, but good to keep in mind
    seq = int.from_bytes(payload[10:18], "big")
    msg_count = int.from_bytes(payload[18:20], "big")

    offset = 20
    frames: list[bytes] = []

    for _ in range(msg_count):
        if offset + 2 > len(payload):
            break  # malformed / truncated
        msg_len = int.from_bytes(payload[offset:offset+2], "big")
        offset += 2

        if offset + msg_len > len(payload):
            break  # malformed / truncated

        msg = payload[offset:offset+msg_len]
        offset += msg_len

        # itchfeed expects: 0x00 <1-byte length> <msg>
        if msg_len > 255:
            # ITCH messages are small, so this would be unexpected
            continue

        frame = b"\x00" + bytes([msg_len]) + msg
        frames.append(frame)

    return frames


def main():
    if len(sys.argv) != 3:
        print("Usage: pcap_to_itch.py <input.pcap> <output.itch>")
        sys.exit(1)

    pcap_path = sys.argv[1]
    out_path = sys.argv[2]

    written_frames = 0
    packets_seen = 0

    with PcapReader(pcap_path) as pcap, open(out_path, "wb") as out_f:
        for pkt in pcap:
            packets_seen += 1
            if not pkt.haslayer(UDP):
                continue

            udp = pkt[UDP]
            payload = bytes(udp.payload)
            if not payload:
                continue

            frames = moldudp64_payload_to_itch_frames(payload)
            for frame in frames:
                out_f.write(frame)
                written_frames += 1

    print(
        f"Processed {packets_seen} packets, wrote {written_frames} ITCH "
        f"messages to: {out_path}"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Fast converter: Databento Nasdaq TotalView-ITCH PCAP (MoldUDP64)
→ raw ITCH stream suitable for itchfeed.MessageParser.

Expected payload format (MoldUDP64):
    [10 bytes] session id (ASCII)
    [8 bytes]  sequence number (big-endian)
    [2 bytes]  message count (big-endian)
    Then, for each message:
        [2 bytes] message_length (big-endian)
        [N bytes] ITCH message body

We convert each ITCH message into:
    0x00 <1-byte length> <ITCH bytes>

which is what itchfeed expects.
"""

import argparse
import time
from pathlib import Path

import dpkt


def moldudp64_to_itch_frames(payload: bytes, out_f):
    """
    Parse a single MoldUDP64 payload and write framed ITCH messages directly to out_f.

    out_f.write(b"\x00" + bytes([length]) + msg_bytes)
    """
    if len(payload) < 20:
        return 0

    # MoldUDP64 header
    # 0–9:  session (10 bytes, ASCII)
    # 10–17: sequence number (8 bytes, big-endian)
    # 18–19: message count (2 bytes, big-endian)
    msg_count = int.from_bytes(payload[18:20], "big")
    data = payload[20:]
    offset = 0
    total_len = len(data)
    written = 0

    for _ in range(msg_count):
        if offset + 2 > total_len:
            break
        msg_len = int.from_bytes(data[offset:offset + 2], "big")
        offset += 2

        if msg_len <= 0:
            break
        if offset + msg_len > total_len:
            break

        msg = data[offset:offset + msg_len]
        offset += msg_len

        # itchfeed expects 0x00 + 1-byte length
        if msg_len > 255:
            # ITCH 5.0 messages are normally < 255 bytes; skip if not
            continue

        out_f.write(b"\x00")
        out_f.write(bytes((msg_len,)))
        out_f.write(msg)
        written += 1

    return written


def pcap_to_itch(pcap_path: Path, itch_out_path: Path, udp_port: int | None = None):
    packets_seen = 0
    packets_used = 0
    msgs_written = 0
    start_time = time.time()
    last_packet_log = 0
    last_msg_log = 0

    print(f"[START] Converting PCAP to ITCH format")
    print(f"  Input:  {pcap_path}")
    print(f"  Output: {itch_out_path}")
    if udp_port is not None:
        print(f"  UDP Port filter: {udp_port}")
    print()

    with pcap_path.open("rb") as f_in, itch_out_path.open("wb") as f_out:
        pcap = dpkt.pcap.Reader(f_in)

        for ts, buf in pcap:
            packets_seen += 1
            
            # Progress logging every 100k packets
            if packets_seen - last_packet_log >= 100_000:
                elapsed = time.time() - start_time
                packet_rate = packets_seen / elapsed if elapsed > 0 else 0
                msg_rate = msgs_written / elapsed if elapsed > 0 else 0
                print(
                    f"[PROGRESS] Packets: {packets_seen:,} | "
                    f"UDP packets used: {packets_used:,} | "
                    f"Messages written: {msgs_written:,} | "
                    f"Time: {elapsed:.1f}s | "
                    f"Rate: {packet_rate:,.0f} pkt/s, {msg_rate:,.0f} msg/s"
                )
                last_packet_log = packets_seen
            
            try:
                eth = dpkt.ethernet.Ethernet(buf)
            except Exception:
                continue

            ip = eth.data
            # Could be IPv4 or IPv6; handle both
            if not isinstance(ip, (dpkt.ip.IP, dpkt.ip6.IP6)):
                continue

            udp = ip.data
            if not isinstance(udp, dpkt.udp.UDP):
                continue

            if udp_port is not None:
                if udp.sport != udp_port and udp.dport != udp_port: # type: ignore
                    continue

            payload = udp.data
            if not payload:
                continue

            written = moldudp64_to_itch_frames(payload, f_out)
            if written > 0:
                packets_used += 1
                msgs_written += written
                
                # Progress logging every 100k messages
                if msgs_written - last_msg_log >= 100_000:
                    elapsed = time.time() - start_time
                    packet_rate = packets_seen / elapsed if elapsed > 0 else 0
                    msg_rate = msgs_written / elapsed if elapsed > 0 else 0
                    print(
                        f"[PROGRESS] Packets: {packets_seen:,} | "
                        f"UDP packets used: {packets_used:,} | "
                        f"Messages written: {msgs_written:,} | "
                        f"Time: {elapsed:.1f}s | "
                        f"Rate: {packet_rate:,.0f} pkt/s, {msg_rate:,.0f} msg/s"
                    )
                    last_msg_log = msgs_written

    # Final summary
    elapsed = time.time() - start_time
    packet_rate = packets_seen / elapsed if elapsed > 0 else 0
    msg_rate = msgs_written / elapsed if elapsed > 0 else 0
    avg_msgs_per_packet = msgs_written / packets_used if packets_used > 0 else 0
    
    print()
    print("=" * 80)
    print("[COMPLETE] PCAP to ITCH conversion finished")
    print("=" * 80)
    print(f"  Total packets processed:     {packets_seen:,}")
    print(f"  UDP packets used:           {packets_used:,} ({packets_used/packets_seen*100:.1f}% of total)")
    print(f"  ITCH messages written:      {msgs_written:,}")
    print(f"  Avg messages per UDP packet: {avg_msgs_per_packet:.1f}")
    print(f"  Processing time:           {elapsed:.1f}s")
    print(f"  Packet processing rate:     {packet_rate:,.0f} packets/s")
    print(f"  Message extraction rate:    {msg_rate:,.0f} messages/s")
    print(f"  Output file:                {itch_out_path}")
    print("=" * 80)


def main():
    ap = argparse.ArgumentParser(
        description="Fast PCAP (MoldUDP64) → raw ITCH converter for itchfeed."
    )
    ap.add_argument("pcap_file", help="Path to .pcap file")
    ap.add_argument("itch_out", help="Output raw ITCH file path")
    ap.add_argument(
        "--port",
        type=int,
        default=None,
        help="Optional UDP port filter (Databento docs may list it).",
    )
    args = ap.parse_args()

    pcap_to_itch(Path(args.pcap_file), Path(args.itch_out), args.port)


if __name__ == "__main__":
    main()

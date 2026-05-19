"""Command-line interface for the safe buffer overflow lab."""

from __future__ import annotations

import argparse

from .pattern import cyclic, find_offset, printable_chunks
from .stack_simulator import StackFrame, UnsafeCopyError
from .visualizer import render_layout_diff


def _cmd_pattern(args: argparse.Namespace) -> int:
    data = cyclic(args.length)
    for chunk in printable_chunks(data):
        print(chunk)
    return 0


def _cmd_find_offset(args: argparse.Namespace) -> int:
    offset = find_offset(args.needle, length=args.length)
    if offset == -1:
        print("needle not found")
        return 1
    print(offset)
    return 0


def _overflow_payload(args: argparse.Namespace, frame: StackFrame) -> tuple[bytes, bytes]:
    control_marker = b"BBBB"
    payload = b"A" * args.payload_size
    if args.marker:
        control_marker = args.marker.encode("ascii")[:4].ljust(4, b"!")
        payload = b"A" * frame.return_address_offset + control_marker
    return payload, control_marker


def _cmd_demo_overflow(args: argparse.Namespace) -> int:
    frame = StackFrame(buffer_size=args.buffer_size, canary_enabled=args.canary)
    payload, control_marker = _overflow_payload(args, frame)

    result = frame.unsafe_copy(payload, control_marker=control_marker)
    print(result.summary)
    print(f"payload_size={result.payload_size}")
    print(f"buffer_size={result.buffer_size}")
    print(f"canary_enabled={result.canary_enabled}")
    print(f"canary_ok={result.canary_ok}")
    print(f"saved_frame_pointer={result.saved_frame_pointer!r}")
    print(f"return_address={result.return_address!r}")
    return 2 if result.aborted else 0


def _cmd_show_layout(args: argparse.Namespace) -> int:
    frame = StackFrame(buffer_size=args.buffer_size, canary_enabled=args.canary)
    before = frame.layout()
    payload, control_marker = _overflow_payload(args, frame)
    result = frame.unsafe_copy(payload, control_marker=control_marker)
    print(render_layout_diff(before, frame.layout(), result))
    return 2 if result.aborted else 0


def _cmd_safe_copy(args: argparse.Namespace) -> int:
    frame = StackFrame(buffer_size=args.buffer_size, canary_enabled=args.canary)
    payload = b"A" * args.payload_size
    try:
        result = frame.bounded_copy(payload)
    except UnsafeCopyError as exc:
        print(f"REJECTED: {exc}")
        return 1

    print(result.summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe local buffer-overflow lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pattern_parser = subparsers.add_parser("pattern", help="generate a cyclic pattern")
    pattern_parser.add_argument("--length", type=int, default=128)
    pattern_parser.set_defaults(func=_cmd_pattern)

    offset_parser = subparsers.add_parser("find-offset", help="find an offset in a pattern")
    offset_parser.add_argument("--needle", required=True)
    offset_parser.add_argument("--length", type=int, default=8192)
    offset_parser.set_defaults(func=_cmd_find_offset)

    overflow_parser = subparsers.add_parser("demo-overflow", help="simulate an unsafe copy")
    overflow_parser.add_argument("--payload-size", type=int, default=80)
    overflow_parser.add_argument("--buffer-size", type=int, default=64)
    overflow_parser.add_argument("--canary", action="store_true")
    overflow_parser.add_argument("--marker", help="4-byte marker to place at the return address")
    overflow_parser.set_defaults(func=_cmd_demo_overflow)

    layout_parser = subparsers.add_parser("show-layout", help="show stack layout before and after a copy")
    layout_parser.add_argument("--payload-size", type=int, default=80)
    layout_parser.add_argument("--buffer-size", type=int, default=64)
    layout_parser.add_argument("--canary", action="store_true")
    layout_parser.add_argument("--marker", help="4-byte marker to place at the return address")
    layout_parser.set_defaults(func=_cmd_show_layout)

    safe_parser = subparsers.add_parser("safe-copy", help="simulate a bounded copy")
    safe_parser.add_argument("--payload-size", type=int, default=80)
    safe_parser.add_argument("--buffer-size", type=int, default=64)
    safe_parser.add_argument("--canary", action="store_true")
    safe_parser.set_defaults(func=_cmd_safe_copy)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

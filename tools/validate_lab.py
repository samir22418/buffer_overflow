"""Smoke validation for the safe buffer-overflow lab."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from buffer_lab import StackFrame, cyclic, find_offset  # noqa: E402
from buffer_lab.stack_simulator import UnsafeCopyError  # noqa: E402


def main() -> int:
    pattern = cyclic(128)
    needle = pattern[40:44]
    assert find_offset(needle, length=128) == 40

    frame = StackFrame(buffer_size=8)
    result = frame.unsafe_copy(b"A" * frame.return_address_offset + b"BBBB")
    assert result.control_marker_seen
    assert result.return_address == b"BBBB"

    protected = StackFrame(buffer_size=8, canary_enabled=True)
    protected_result = protected.unsafe_copy(b"A" * 20)
    assert protected_result.aborted
    assert not protected_result.canary_ok

    try:
        frame.bounded_copy(b"A" * 9)
    except UnsafeCopyError:
        pass
    else:
        raise AssertionError("bounded_copy accepted oversized input")

    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

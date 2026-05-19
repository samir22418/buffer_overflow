from __future__ import annotations

import unittest

from buffer_lab import StackFrame, cyclic, find_offset, render_layout_diff
from buffer_lab.stack_simulator import UnsafeCopyError


class PatternTests(unittest.TestCase):
    def test_find_offset_accepts_bytes(self) -> None:
        pattern = cyclic(128)
        self.assertEqual(find_offset(pattern[52:56], length=128), 52)

    def test_find_offset_accepts_little_endian_hex_register_value(self) -> None:
        pattern = cyclic(128)
        needle = int.from_bytes(pattern[24:28], byteorder="little")
        self.assertEqual(find_offset(hex(needle), length=128), 24)


class StackSimulatorTests(unittest.TestCase):
    def test_unsafe_copy_can_replace_return_address_with_marker(self) -> None:
        frame = StackFrame(buffer_size=8)
        payload = b"A" * frame.return_address_offset + b"BBBB"
        result = frame.unsafe_copy(payload)
        self.assertTrue(result.control_marker_seen)
        self.assertEqual(result.return_address, b"BBBB")

    def test_canary_detects_overflow_before_return_address_use(self) -> None:
        frame = StackFrame(buffer_size=8, canary_enabled=True)
        result = frame.unsafe_copy(b"A" * 20)
        self.assertTrue(result.aborted)
        self.assertFalse(result.canary_ok)

    def test_bounded_copy_rejects_oversized_payload(self) -> None:
        frame = StackFrame(buffer_size=8)
        with self.assertRaises(UnsafeCopyError):
            frame.bounded_copy(b"A" * 9)


class VisualizerTests(unittest.TestCase):
    def test_render_layout_diff_marks_return_address_marker(self) -> None:
        frame = StackFrame(buffer_size=8)
        before = frame.layout()
        marker = b"TEST"
        payload = b"A" * frame.return_address_offset + marker
        result = frame.unsafe_copy(payload, control_marker=marker)

        output = render_layout_diff(before, frame.layout(), result)

        self.assertIn("OVERWRITE: return address replaced with marker", output)
        self.assertIn("return_address", output)
        self.assertIn("marker", output)
        self.assertIn("|TEST|", output)


if __name__ == "__main__":
    unittest.main()

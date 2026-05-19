"""A safe stack-frame simulator for buffer overflow training."""

from __future__ import annotations

from dataclasses import dataclass


class UnsafeCopyError(ValueError):
    """Raised when a bounded copy rejects oversized input."""


@dataclass(frozen=True)
class CopyResult:
    payload_size: int
    buffer_size: int
    canary_enabled: bool
    canary_ok: bool
    saved_frame_pointer: bytes
    return_address: bytes
    overflowed: bool
    control_marker_seen: bool
    aborted: bool

    @property
    def summary(self) -> str:
        if self.aborted:
            return "ABORTED: stack canary detected corruption"
        if self.control_marker_seen:
            return "OVERWRITE: return address replaced with marker"
        if self.overflowed:
            return "OVERFLOW: adjacent stack metadata changed"
        return "OK: payload stayed inside the buffer"


class StackFrame:
    """Model a simple stack frame without executing attacker-controlled bytes."""

    def __init__(
        self,
        *,
        buffer_size: int = 64,
        canary_enabled: bool = False,
        canary: bytes = b"CNR!",
        saved_frame_pointer: bytes = b"EBP!",
        return_address: bytes = b"RET0",
    ) -> None:
        if buffer_size <= 0:
            raise ValueError("buffer_size must be positive")
        self.buffer_size = buffer_size
        self.canary_enabled = canary_enabled
        self.initial_canary = canary
        self.initial_saved_frame_pointer = saved_frame_pointer
        self.initial_return_address = return_address
        self._field_width = 4

        for field_name, field_value in {
            "canary": canary,
            "saved_frame_pointer": saved_frame_pointer,
            "return_address": return_address,
        }.items():
            if len(field_value) != self._field_width:
                raise ValueError(f"{field_name} must be exactly 4 bytes")

        self.reset()

    def reset(self) -> None:
        self._memory = bytearray(b"\x00" * self.buffer_size)
        if self.canary_enabled:
            self._memory.extend(self.initial_canary)
        self._memory.extend(self.initial_saved_frame_pointer)
        self._memory.extend(self.initial_return_address)

    @property
    def saved_frame_pointer_offset(self) -> int:
        return self.buffer_size + (self._field_width if self.canary_enabled else 0)

    @property
    def return_address_offset(self) -> int:
        return self.saved_frame_pointer_offset + self._field_width

    @property
    def canary(self) -> bytes | None:
        if not self.canary_enabled:
            return None
        return bytes(self._memory[self.buffer_size : self.buffer_size + self._field_width])

    @property
    def saved_frame_pointer(self) -> bytes:
        start = self.saved_frame_pointer_offset
        return bytes(self._memory[start : start + self._field_width])

    @property
    def return_address(self) -> bytes:
        start = self.return_address_offset
        return bytes(self._memory[start : start + self._field_width])

    def unsafe_copy(self, payload: bytes, *, control_marker: bytes = b"BBBB") -> CopyResult:
        """Copy bytes as an unsafe C string function would, overflowing metadata."""

        self.reset()
        for index, value in enumerate(payload):
            if index >= len(self._memory):
                break
            self._memory[index] = value

        canary_ok = self.canary is None or self.canary == self.initial_canary
        overflowed = (
            len(payload) > self.buffer_size
            or self.saved_frame_pointer != self.initial_saved_frame_pointer
            or self.return_address != self.initial_return_address
        )
        control_marker_seen = self.return_address == control_marker
        aborted = self.canary_enabled and not canary_ok

        return CopyResult(
            payload_size=len(payload),
            buffer_size=self.buffer_size,
            canary_enabled=self.canary_enabled,
            canary_ok=canary_ok,
            saved_frame_pointer=self.saved_frame_pointer,
            return_address=self.return_address,
            overflowed=overflowed,
            control_marker_seen=control_marker_seen,
            aborted=aborted,
        )

    def bounded_copy(self, payload: bytes) -> CopyResult:
        """Reject input that would not fit in the fixed buffer."""

        if len(payload) > self.buffer_size:
            raise UnsafeCopyError(
                f"payload is {len(payload)} bytes, but buffer is {self.buffer_size} bytes"
            )
        return self.unsafe_copy(payload)

    def layout(self) -> list[tuple[str, int, bytes]]:
        rows: list[tuple[str, int, bytes]] = [
            ("buffer", 0, bytes(self._memory[: self.buffer_size])),
        ]
        if self.canary_enabled:
            rows.append(("canary", self.buffer_size, self.canary or b""))
        rows.append(("saved_frame_pointer", self.saved_frame_pointer_offset, self.saved_frame_pointer))
        rows.append(("return_address", self.return_address_offset, self.return_address))
        return rows

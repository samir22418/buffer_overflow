"""Memory layout rendering helpers for the safe stack-frame simulator."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .stack_simulator import CopyResult

LayoutSnapshot = Sequence[tuple[str, int, bytes]]


@dataclass(frozen=True)
class LayoutDiffRow:
    field: str
    offset: int
    size: int
    before: bytes
    after: bytes
    status: str


def diff_layout(
    before: LayoutSnapshot,
    after: LayoutSnapshot,
    result: CopyResult,
) -> list[LayoutDiffRow]:
    """Compare two stack-frame layouts after a simulated copy."""

    after_by_field = {field: (offset, data) for field, offset, data in after}
    rows: list[LayoutDiffRow] = []

    for field, offset, before_data in before:
        after_offset, after_data = after_by_field[field]
        rows.append(
            LayoutDiffRow(
                field=field,
                offset=after_offset,
                size=len(after_data),
                before=before_data,
                after=after_data,
                status=_status_for(field, before_data, after_data, result),
            )
        )

    return rows


def render_layout_diff(
    before: LayoutSnapshot,
    after: LayoutSnapshot,
    result: CopyResult,
    *,
    preview_width: int = 12,
) -> str:
    """Render a compact before/after view of stack memory."""

    rows = diff_layout(before, after, result)
    lines = [
        result.summary,
        f"payload_size={result.payload_size}",
        f"buffer_size={result.buffer_size}",
        f"canary_enabled={result.canary_enabled}",
        f"canary_ok={result.canary_ok}",
        "",
        "offset       field                  size  status       before -> after",
        "-----------  ---------------------  ----  -----------  ----------------",
    ]

    for row in rows:
        end = row.offset + row.size - 1
        offset_range = f"{row.offset:04d}-{end:04d}"
        before_preview = _preview_bytes(row.before, preview_width)
        after_preview = _preview_bytes(row.after, preview_width)
        lines.append(
            f"{offset_range:<11}  {row.field:<21}  {row.size:>4}  "
            f"{row.status:<11}  {before_preview} -> {after_preview}"
        )

    lines.extend(
        [
            "",
            "Preview format: hex bytes |ascii|. A dot means a non-printable byte.",
        ]
    )
    return "\n".join(lines)


def _status_for(field: str, before: bytes, after: bytes, result: CopyResult) -> str:
    if before == after:
        return "same"
    if field == "buffer":
        return "written"
    if field == "canary":
        return "corrupted" if not result.canary_ok else "changed"
    if field == "saved_frame_pointer":
        return "overwritten"
    if field == "return_address":
        return "marker" if result.control_marker_seen else "overwritten"
    return "changed"


def _preview_bytes(data: bytes, width: int) -> str:
    if not data:
        return "<empty>"

    shown = data[:width]
    hex_text = " ".join(f"{byte:02x}" for byte in shown)
    ascii_text = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in shown)
    suffix = f" ... ({len(data)} bytes)" if len(data) > width else ""
    return f"{hex_text} |{ascii_text}|{suffix}"

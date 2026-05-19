"""Safe local buffer-overflow training helpers."""

from .pattern import cyclic, find_offset
from .stack_simulator import CopyResult, StackFrame, UnsafeCopyError
from .visualizer import LayoutDiffRow, diff_layout, render_layout_diff

__all__ = [
    "CopyResult",
    "LayoutDiffRow",
    "StackFrame",
    "UnsafeCopyError",
    "cyclic",
    "diff_layout",
    "find_offset",
    "render_layout_diff",
]

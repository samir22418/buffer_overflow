"""Cyclic pattern generation for local offset-finding exercises.

The implementation uses a de Bruijn sequence so every 4-byte window is unique
for the configured alphabet until the sequence repeats.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_ALPHABET = b"abcdefghijklmnopqrstuvwxyz"
DEFAULT_WINDOW = 4


def _de_bruijn(alphabet: bytes, subsequence_length: int) -> bytes:
    if subsequence_length < 1:
        raise ValueError("subsequence_length must be at least 1")
    if len(set(alphabet)) != len(alphabet):
        raise ValueError("alphabet must contain unique bytes")

    alphabet_size = len(alphabet)
    sequence: list[int] = []
    working = [0] * (alphabet_size * subsequence_length)

    def db(t: int, p: int) -> None:
        if t > subsequence_length:
            if subsequence_length % p == 0:
                sequence.extend(working[1 : p + 1])
            return

        working[t] = working[t - p]
        db(t + 1, p)
        for j in range(working[t - p] + 1, alphabet_size):
            working[t] = j
            db(t + 1, t)

    db(1, 1)
    return bytes(alphabet[index] for index in sequence)


def cyclic(
    length: int,
    *,
    alphabet: bytes = DEFAULT_ALPHABET,
    window: int = DEFAULT_WINDOW,
) -> bytes:
    """Return a deterministic cyclic pattern with unique 4-byte windows."""

    if length < 0:
        raise ValueError("length must be non-negative")
    sequence = _de_bruijn(alphabet, window)
    if not sequence:
        return b""

    repeats = (length // len(sequence)) + 1
    return (sequence * repeats)[:length]


def _needle_to_bytes(needle: bytes | str | int) -> bytes:
    if isinstance(needle, bytes):
        return needle

    if isinstance(needle, int):
        if needle < 0 or needle > 0xFFFFFFFF:
            raise ValueError("integer needle must fit in 32 bits")
        return needle.to_bytes(4, byteorder="little")

    normalized = needle.strip()
    if normalized.startswith(("0x", "0X")):
        value = int(normalized, 16)
        return _needle_to_bytes(value)
    return normalized.encode("latin1")


def find_offset(
    needle: bytes | str | int,
    *,
    length: int = 8192,
    alphabet: bytes = DEFAULT_ALPHABET,
    window: int = DEFAULT_WINDOW,
) -> int:
    """Find a byte sequence inside a cyclic pattern.

    Hex integer needles are interpreted as little-endian register values, which
    matches the way overwritten 32-bit return addresses are commonly reported.
    """

    pattern = cyclic(length, alphabet=alphabet, window=window)
    return pattern.find(_needle_to_bytes(needle))


def printable_chunks(data: bytes, *, width: int = 32) -> Iterable[str]:
    """Yield fixed-width printable chunks for CLI display."""

    for start in range(0, len(data), width):
        yield data[start : start + width].decode("ascii")

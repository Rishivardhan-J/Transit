"""Streaming helpers for the Amazon Last Mile JSON files (multi-GB, contain bare NaN tokens)."""
from typing import Iterator, Tuple

import ijson


class _NaNToNull:
    """File wrapper that rewrites bare `NaN` tokens to `null` so strict JSON parsers accept them."""

    def __init__(self, f):
        self.f, self.carry = f, b""

    def read(self, n=-1):
        if n == 0:  # ijson probes the stream type with read(0)
            return b""
        # "NaN" -> "null" grows by 1/3 at most; read less so we never return more than `n` bytes
        chunk = self.f.read(max(1, (n if n > 0 else 1 << 20) // 2))
        data, self.carry = self.carry + chunk, b""
        if chunk and not data.endswith(b"NaN"):  # hold back a tail that might be the start of a split "NaN"
            for k in (2, 1):
                if data.endswith(b"NaN"[:k]):
                    data, self.carry = data[:-k], data[-k:]
                    break
        return data.replace(b"NaN", b"null")


def iter_routes(path) -> Iterator[Tuple[str, dict]]:
    """Yield (route_id, route_dict) one route at a time without loading the whole file."""
    with open(path, "rb") as raw:
        yield from ijson.kvitems(_NaNToNull(raw), "", use_float=True)

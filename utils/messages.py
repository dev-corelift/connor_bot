"""Message formatting helpers."""

from __future__ import annotations

import random
from typing import Iterable, List


def split_message(text: str, max_length: int = 2000) -> Iterable[str]:
    if len(text) <= max_length:
        yield text
        return

    words: List[str] = text.split()
    chunk: List[str] = []
    size = 0
    for word in words:
        word_len = len(word) + 1
        if size + word_len > max_length:
            if chunk:
                yield " ".join(chunk)
            chunk = [word]
            size = len(word)
        else:
            chunk.append(word)
            size += word_len
    if chunk:
        yield " ".join(chunk)


def apply_nervous_stutter(text: str, intensity: float = 0.2) -> str:
    words = text.split()
    stuttered: List[str] = []
    for word in words:
        if random.random() < max(0.0, min(1.0, intensity)):
            stuttered.append(f"{word}-{word}")
        else:
            stuttered.append(word)
    return " ".join(stuttered)

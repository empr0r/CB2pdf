"""Locale-independent ordering of archive paths."""

import re
import unicodedata


def normalized_name(name: str) -> str:
    return unicodedata.normalize("NFC", name.replace("\\", "/"))


def natural_key(name: str) -> tuple[object, ...]:
    """Compare components case-insensitively, ASCII runs numerically, then raw spelling.

    Equal numeric values use fewer leading zeros first. Original spelling provides
    a final tie break, so ZIP enumeration and host locale never affect ordering.
    """
    normalized = normalized_name(name)
    components = []
    for component in normalized.casefold().split("/"):
        tokens: list[tuple[int, str | int, int]] = []
        for token in re.split(r"([0-9]+)", component):
            if token.isascii() and token.isdigit():
                tokens.append((1, int(token), len(token)))
            else:
                tokens.append((0, token, 0))
        components.append(tuple(tokens))
    return (tuple(components), normalized, name)

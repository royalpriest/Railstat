"""Masking for personal data that reports don't need in full."""

MASK = "•"


def mask_name(name: str) -> str:
    """'Maria Gonzalez' -> 'M. G••••••'; 'Cher' -> 'C•••'. Keeps initials only."""
    parts = name.split()
    if not parts:
        return ""
    if len(parts) == 1:
        word = parts[0]
        return word[0] + MASK * (len(word) - 1)
    last = parts[-1]
    return f"{parts[0][0]}. {last[0]}{MASK * (len(last) - 1)}"


def display_name(name: str, show_names: bool) -> str:
    return name if show_names else mask_name(name)

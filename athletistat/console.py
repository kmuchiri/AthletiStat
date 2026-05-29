"""
console.py - Shared terminal styling utilities for AthletiStat CLI output.

Usage:
    from athletistat.console import cprint, Colors, Symbols
    cprint("All done!", Colors.GREEN, bold=True, prefix=Symbols.OK)
"""


class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Foreground
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    # Bright variants
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"


class Symbols:
    OK      = "✔"
    FAIL    = "✖"
    WARN    = "⚠"
    INFO    = "i"
    ARROW   = "→"
    BULLET  = "•"
    ROCKET  = ">>"
    CLOCK   = "⏱"
    SKIP    = "⏭"
    SAVE    = "▼"
    SEARCH  = "⌕"
    GEAR    = "⚙"
    MERGE   = "⋈"


def cprint(message: str, color: str = "", bold: bool = False, prefix: str = "", dim: bool = False) -> None:
    """
    Print a styled message to the terminal.

    Args:
        message (str): The text to print.
        color   (str): An ANSI color code from Colors (e.g. Colors.GREEN).
        bold    (bool): Whether to apply bold formatting.
        prefix  (str): Optional symbol/prefix prepended to the message.
        dim     (bool): Whether to apply dim (muted) formatting.
    """
    style = ""
    if bold:
        style += Colors.BOLD
    if dim:
        style += Colors.DIM
    style += color

    text = f"{prefix} {message}" if prefix else message
    print(f"{style}{text}{Colors.RESET}")


def header(title: str, char: str = "─", width: int = 52) -> None:
    """Print a styled section header."""
    line = char * width
    cprint(line, Colors.BRIGHT_BLUE, bold=True)
    cprint(f"  {title}", Colors.BRIGHT_WHITE, bold=True)
    cprint(line, Colors.BRIGHT_BLUE, bold=True)


def divider(char: str = "─", width: int = 52, color: str = Colors.DIM + Colors.WHITE) -> None:
    """Print a thin divider line."""
    print(f"{color}{char * width}{Colors.RESET}")


def success(message: str, detail: str = "") -> None:
    """Print a green success message."""
    cprint(message, Colors.BRIGHT_GREEN, bold=True, prefix=Symbols.OK)
    if detail:
        cprint(f"  {detail}", Colors.GREEN, dim=True)


def warn(message: str) -> None:
    """Print a yellow warning message."""
    cprint(message, Colors.BRIGHT_YELLOW, prefix=Symbols.WARN)


def error(message: str) -> None:
    """Print a red error message."""
    cprint(message, Colors.BRIGHT_RED, bold=True, prefix=Symbols.FAIL)


def info(message: str) -> None:
    """Print a cyan informational message."""
    cprint(message, Colors.CYAN, prefix=Symbols.INFO)


def step(message: str) -> None:
    """Print a blue step/action message."""
    cprint(message, Colors.BRIGHT_BLUE, prefix=Symbols.ARROW)

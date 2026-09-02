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
    WHITE   = ""           # Use terminal default foreground (avoids white-on-white)

    # Bright variants
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = ""    # Use terminal default foreground (avoids white-on-white)


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


import threading
from tqdm import tqdm


class ProgressBar:
    """
    A thread-safe, static terminal progress bar that updates in-place.

    Backed by ``tqdm`` so that:
    - The bar occupies exactly one line and rewrites it in place.
    - Elapsed time and estimated time-to-completion are shown automatically.
    - Messages printed via :meth:`write` appear *above* the bar without
      disrupting it (uses ``tqdm.write`` internally).

    Usage::

        bar = ProgressBar(total=100, label="SEASONS 2026")
        bar.write("Saved data/processing/output/...")   # printed above bar
        bar.update()        # increments by 1
        bar.update(5)       # increments by 5
        bar.finish()        # finalizes and moves to the next line
    """

    def __init__(self, total: int, label: str = "", width: int = 30):
        """
        Initialize the progress bar.

        Args:
            total (int): Total number of items.
            label (str): Optional label displayed before the bar.
            width (int): Character width of the bar fill. Defaults to 30.
        """
        self.total = total
        self._lock = threading.Lock()
        self._bar = tqdm(
            total=total,
            desc=f"\033[1m\033[96m{label}\033[0m" if label else "",
            bar_format=(
                "{desc} \033[2m[\033[0m"
                "\033[92m{bar}\033[0m"
                "\033[2m]\033[0m"
                " \033[1m{percentage:5.1f}%\033[0m"
                "  \033[2m{n}/{total}  elapsed {elapsed}\033[0m"
            ),
            ncols=None,        # auto-detect terminal width
            ascii=False,
            leave=True,
            miniters=1,
            dynamic_ncols=True,
        )
        # Override the bar fill/empty characters to match original style
        self._bar.bar_format = self._bar.bar_format  # keep reference

    def write(self, message: str) -> None:
        """
        Print *message* above the progress bar without disrupting it.

        This is thread-safe and can be called from worker threads.

        Args:
            message (str): The text to print above the bar.
        """
        tqdm.write(message)

    def update(self, n: int = 1) -> None:
        """
        Increment progress by *n* and redraw the bar.

        Args:
            n (int): Number of items completed. Defaults to 1.
        """
        with self._lock:
            self._bar.update(n)

    def finish(self) -> None:
        """Finalize the bar at 100% and move to the next line."""
        with self._lock:
            remaining = self.total - self._bar.n
            if remaining > 0:
                self._bar.update(remaining)
            self._bar.close()

package console

import (
	"fmt"
	"strings"
	"sync"

	"github.com/schollz/progressbar/v3"
)

// ANSI terminal color codes matching Python Colors class.
const (
	Reset = "\033[0m"
	Bold  = "\033[1m"
	Dim   = "\033[2m"

	// Standard foreground
	Red     = "\033[31m"
	Green   = "\033[32m"
	Yellow  = "\033[33m"
	Blue    = "\033[34m"
	Magenta = "\033[35m"
	Cyan    = "\033[36m"
	White   = ""

	// Bright foreground
	BrightRed     = "\033[91m"
	BrightGreen   = "\033[92m"
	BrightYellow  = "\033[93m"
	BrightBlue    = "\033[94m"
	BrightMagenta = "\033[95m"
	BrightCyan    = "\033[96m"
	BrightWhite   = ""
)

// Symbols matching Python Symbols class.
const (
	SymOK     = "✔"
	SymFail   = "✖"
	SymWarn   = "⚠"
	SymInfo   = "i"
	SymArrow  = "→"
	SymBullet = "•"
	SymRocket = ">>"
	SymClock  = "⏱"
	SymSkip   = "⏭"
	SymSave   = "▼"
	SymSearch = "⌕"
	SymGear   = "⚙"
	SymMerge  = "⋈"
)

// Cprint prints a styled message to standard output.
func Cprint(message string, color string, bold bool, prefix string, dim bool) {
	style := ""
	if bold {
		style += Bold
	}
	if dim {
		style += Dim
	}
	style += color

	text := message
	if prefix != "" {
		text = fmt.Sprintf("%s %s", prefix, message)
	}

	fmt.Printf("%s%s%s\n", style, text, Reset)
}

// Header prints a styled section header.
func Header(title string, char string, width int) {
	if char == "" {
		char = "─"
	}
	if width <= 0 {
		width = 52
	}
	line := strings.Repeat(char, width)
	Cprint(line, BrightBlue, true, "", false)
	Cprint(fmt.Sprintf("  %s", title), BrightWhite, true, "", false)
	Cprint(line, BrightBlue, true, "", false)
}

// Divider prints a thin divider line.
func Divider(char string, width int, color string) {
	if char == "" {
		char = "─"
	}
	if width <= 0 {
		width = 52
	}
	if color == "" {
		color = Dim + White
	}
	fmt.Printf("%s%s%s\n", color, strings.Repeat(char, width), Reset)
}

// Success prints a green success message with optional detail.
func Success(message string, detail ...string) {
	Cprint(message, BrightGreen, true, SymOK, false)
	if len(detail) > 0 && detail[0] != "" {
		Cprint(fmt.Sprintf("  %s", detail[0]), Green, false, "", true)
	}
}

// Warn prints a yellow warning message.
func Warn(message string) {
	Cprint(message, BrightYellow, false, SymWarn, false)
}

// Error prints a red error message.
func Error(message string) {
	Cprint(message, BrightRed, true, SymFail, false)
}

// Info prints a cyan informational message.
func Info(message string) {
	Cprint(message, Cyan, false, SymInfo, false)
}

// Step prints a blue step/action message.
func Step(message string) {
	Cprint(message, BrightBlue, false, SymArrow, false)
}

// ProgressBar is a thread-safe terminal progress bar that updates in place.
type ProgressBar struct {
	bar   *progressbar.ProgressBar
	lock  sync.Mutex
	total int
}

// NewProgressBar initializes a new progress bar.
func NewProgressBar(total int, label string, width int) *ProgressBar {
	if width <= 0 {
		width = 30
	}

	desc := ""
	if label != "" {
		desc = fmt.Sprintf("%s%s%s%s", Bold, BrightCyan, label, Reset)
	}

	bar := progressbar.NewOptions(total,
		progressbar.OptionSetDescription(desc),
		progressbar.OptionSetWidth(width),
		progressbar.OptionShowCount(),
		progressbar.OptionShowElapsedTimeOnFinish(),
		progressbar.OptionSetTheme(progressbar.Theme{
			Saucer:        "[green]=[reset]",
			SaucerHead:    "[green]>[reset]",
			SaucerPadding: " ",
			BarStart:      "[",
			BarEnd:        "]",
		}),
		progressbar.OptionOnCompletion(func() {
			fmt.Println()
		}),
	)

	return &ProgressBar{
		bar:   bar,
		total: total,
	}
}

// Write prints a message above or around the progress bar safely.
func (p *ProgressBar) Write(message string) {
	p.lock.Lock()
	defer p.lock.Unlock()
	// Clear current line before writing message so progress bar doesn't clash
	fmt.Printf("\r\033[K%s\n", message)
	_ = p.bar.RenderBlank()
}

// Update increments the progress bar by n (default 1).
func (p *ProgressBar) Update(n ...int) {
	p.lock.Lock()
	defer p.lock.Unlock()
	step := 1
	if len(n) > 0 {
		step = n[0]
	}
	_ = p.bar.Add(step)
}

// Finish marks the progress bar complete.
func (p *ProgressBar) Finish() {
	p.lock.Lock()
	defer p.lock.Unlock()
	_ = p.bar.Finish()
}

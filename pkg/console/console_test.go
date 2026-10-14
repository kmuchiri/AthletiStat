package console

import (
	"bytes"
	"io"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func captureOutput(f func()) string {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	f()

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	_, _ = io.Copy(&buf, r)
	return buf.String()
}

func TestConsolePrinters(t *testing.T) {
	out := captureOutput(func() {
		Cprint("Hello Test", Green, true, SymOK, false)
	})
	assert.Contains(t, out, "Hello Test")
	assert.Contains(t, out, SymOK)

	out = captureOutput(func() {
		Header("TEST HEADER", "─", 30)
	})
	assert.Contains(t, out, "TEST HEADER")

	out = captureOutput(func() {
		Success("Job completed", "Details here")
	})
	assert.Contains(t, out, "Job completed")
	assert.Contains(t, out, "Details here")

	out = captureOutput(func() {
		Warn("Warning message")
		Error("Error message")
		Info("Info message")
		Step("Step message")
	})
	assert.Contains(t, out, "Warning message")
	assert.Contains(t, out, "Error message")
	assert.Contains(t, out, "Info message")
	assert.Contains(t, out, "Step message")
}

func TestProgressBar(t *testing.T) {
	bar := NewProgressBar(10, "TEST", 20)
	assert.NotNil(t, bar)

	bar.Update(2)
	bar.Write("Log line above bar")
	bar.Update(8)
	bar.Finish()
}

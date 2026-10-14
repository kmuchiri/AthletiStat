package main

import (
	"bytes"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCliHelp(t *testing.T) {
	cmd := newRootCmd()
	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)
	cmd.SetArgs([]string{"--help"})

	err := cmd.Execute()
	assert.NoError(t, err)
	output := buf.String()
	assert.Contains(t, output, "AthletiStat - Track & Field Data Pipeline")
	assert.Contains(t, output, "--scraper")
	assert.Contains(t, output, "--preprocessing")
	assert.Contains(t, output, "--create-dataset")
	assert.Contains(t, output, "--combine")
	assert.Contains(t, output, "--split-dataset")
	assert.Contains(t, output, "--fetch-data")
	assert.Contains(t, output, "--year")
	assert.Contains(t, output, "--dataset-info")
	assert.Contains(t, output, "--update-season")
	assert.Contains(t, output, "--no-generate")
}

func TestCliInvalidFlagChoice(t *testing.T) {
	cmd := newRootCmd()
	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)
	cmd.SetArgs([]string{"--scraper", "invalid"})

	err := cmd.Execute()
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "invalid value for --scraper")
}

func TestCliNoArgs(t *testing.T) {
	cmd := newRootCmd()
	buf := new(bytes.Buffer)
	cmd.SetOut(buf)
	cmd.SetErr(buf)
	cmd.SetArgs([]string{})

	err := cmd.Execute()
	assert.NoError(t, err)
}

//go:build !windows

package main

func enableUTF8Console() {}

func steamPathsFromRegistry() []string { return nil }

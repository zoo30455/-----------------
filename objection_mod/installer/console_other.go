//go:build !windows

package main

import "errors"

var errNoElevation = errors.New("повышение прав доступно только в Windows")

func enableUTF8Console() {}

func steamPathsFromRegistry() []string { return nil }

func relaunchAsAdmin(args []string) error { return errNoElevation }

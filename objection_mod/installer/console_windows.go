package main

import (
	"os"
	"path/filepath"
	"strings"
	"syscall"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"
)

func enableUTF8Console() {
	windows.SetConsoleOutputCP(65001)
	windows.SetConsoleCP(65001)
}

func steamPathsFromRegistry() []string {
	var out []string
	for _, k := range []struct {
		root registry.Key
		path string
		val  string
	}{
		{registry.CURRENT_USER, `Software\Valve\Steam`, "SteamPath"},
		{registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Valve\Steam`, "InstallPath"},
		{registry.LOCAL_MACHINE, `SOFTWARE\Valve\Steam`, "InstallPath"},
	} {
		key, err := registry.OpenKey(k.root, k.path, registry.QUERY_VALUE)
		if err != nil {
			continue
		}
		if v, _, err := key.GetStringValue(k.val); err == nil && v != "" {
			out = append(out, v)
		}
		key.Close()
	}
	return out
}

func relaunchAsAdmin(args []string) error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	var params []string
	for _, a := range args {
		params = append(params, syscall.EscapeArg(a))
	}
	verb, _ := windows.UTF16PtrFromString("runas")
	file, _ := windows.UTF16PtrFromString(exe)
	ps, _ := windows.UTF16PtrFromString(strings.Join(params, " "))
	dir, _ := windows.UTF16PtrFromString(filepath.Dir(exe))
	return windows.ShellExecute(0, verb, file, ps, dir, windows.SW_NORMAL)
}

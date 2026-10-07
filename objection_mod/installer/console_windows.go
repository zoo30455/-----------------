package main

import (
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

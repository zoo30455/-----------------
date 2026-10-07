package main

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
)

const (
	gameFolder  = "Phoenix Wright Ace Attorney Trilogy"
	bgmRel      = "PWAAT_Data/StreamingAssets/Sound/bgm"
	backupDir   = "ObjectionMod_backup"
	configName  = "objection_mod.txt"
	listName    = "bgm_list.txt"
	defaultConf = `# Objection Mod — настройки
# source = файл с "Objection! 2001" из первой игры
# target = файлы, которые нужно заменить на него (можно несколько строк)
# Номера — имена файлов из PWAAT_Data\StreamingAssets\Sound\bgm без .unity3d

source = bgm012

# Objection! 2004 (Trials and Tribulations)
target = bgm121

# Objection! 2002 (Justice for All) — впишите номер, если он не bgm0xx ниже.
# Подсказка: после запуска рядом появится bgm_list.txt со всеми треками.
# target = bgm0xx
`
)

func main() {
	enableUTF8Console()
	exitCode := 0
	if err := run(os.Args[1:]); err == errRelaunched {
		return
	} else if err != nil {
		fmt.Println("\nОШИБКА:", err)
		exitCode = 1
	}
	if runtime.GOOS == "windows" {
		fmt.Print("\nНажмите Enter, чтобы закрыть окно...")
		bufio.NewReader(os.Stdin).ReadString('\n')
	}
	os.Exit(exitCode)
}

func run(args []string) error {
	mode := "install"
	var gameArg string
	for _, a := range args {
		switch strings.ToLower(a) {
		case "install", "restore", "uninstall", "list":
			mode = strings.ToLower(a)
		default:
			gameArg = a
		}
	}

	fmt.Println("=== Objection! 2001 Mod для Phoenix Wright: Ace Attorney Trilogy ===")
	game, err := findGame(gameArg)
	if err != nil {
		return err
	}
	fmt.Println("Игра:", game)
	bgm := filepath.Join(game, filepath.FromSlash(bgmRel))
	backup := filepath.Join(game, backupDir)

	if mode != "list" && !canWrite(game) {
		// Игра в Program Files и т.п. — перезапускаемся с правами администратора.
		fmt.Println("Нужны права администратора, запрашиваю...")
		if err := relaunchAsAdmin([]string{mode, game}); err != nil {
			return fmt.Errorf("нет прав на запись в папку игры. Запустите программу правой кнопкой -> \"Запуск от имени администратора\" (%v)", err)
		}
		fmt.Println("Продолжение в новом окне.")
		return errRelaunched
	}

	switch mode {
	case "restore", "uninstall":
		return restore(bgm, backup)
	case "list":
		return writeList(bgm, backup, filepath.Join(exeDir(), listName))
	}

	source, targets, err := loadConfig()
	if err != nil {
		return err
	}
	if err := install(bgm, backup, source, targets); err != nil {
		return err
	}
	listPath := filepath.Join(exeDir(), listName)
	if err := writeList(bgm, backup, listPath); err != nil {
		fmt.Println("(не удалось записать список треков:", err, ")")
	}
	fmt.Println("\nГотово! OBJECTION!  Запускайте игру.")
	fmt.Println("Удалить мод: запустите \"Удалить мод.bat\".")
	return nil
}

var errRelaunched = errors.New("relaunched")

func canWrite(dir string) bool {
	f, err := os.CreateTemp(dir, ".objmod_*")
	if err != nil {
		return false
	}
	f.Close()
	os.Remove(f.Name())
	return true
}

func exeDir() string {
	p, err := os.Executable()
	if err != nil {
		return "."
	}
	return filepath.Dir(p)
}

func isGameDir(p string) bool {
	st, err := os.Stat(filepath.Join(p, filepath.FromSlash(bgmRel)))
	return err == nil && st.IsDir()
}

var vdfPath = regexp.MustCompile(`"path"\s+"([^"]+)"`)

func findGame(arg string) (string, error) {
	var cands []string
	if arg != "" {
		cands = append(cands, arg, filepath.Join(arg, gameFolder))
	}
	// Exe лежит в папке игры или рядом
	d := exeDir()
	cands = append(cands, d, filepath.Dir(d), filepath.Join(d, gameFolder))
	if wd, err := os.Getwd(); err == nil {
		cands = append(cands, wd)
	}

	var steamRoots []string
	steamRoots = append(steamRoots, steamPathsFromRegistry()...)
	steamRoots = append(steamRoots,
		`C:\Program Files (x86)\Steam`, `C:\Program Files\Steam`,
		filepath.Join(os.Getenv("HOME"), ".steam/steam"),
		filepath.Join(os.Getenv("HOME"), ".local/share/Steam"))
	for _, root := range steamRoots {
		libs := []string{root}
		if b, err := os.ReadFile(filepath.Join(root, "steamapps", "libraryfolders.vdf")); err == nil {
			for _, m := range vdfPath.FindAllStringSubmatch(string(b), -1) {
				libs = append(libs, strings.ReplaceAll(m[1], `\\`, `\`))
			}
		}
		for _, l := range libs {
			cands = append(cands, filepath.Join(l, "steamapps", "common", gameFolder))
		}
	}
	for c := 'C'; c <= 'Z'; c++ {
		for _, sub := range []string{`SteamLibrary`, `Steam`, `Games\Steam`, `Program Files (x86)\Steam`} {
			cands = append(cands, filepath.Join(string(c)+`:\`, sub, "steamapps", "common", gameFolder))
		}
	}
	for _, c := range cands {
		if c != "" && isGameDir(c) {
			return c, nil
		}
	}

	fmt.Println("Не нашёл игру автоматически.")
	fmt.Println("Перетащите сюда папку игры (или вставьте путь) и нажмите Enter:")
	line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
	line = strings.Trim(strings.TrimSpace(line), `"`)
	for _, c := range []string{line, filepath.Join(line, gameFolder)} {
		if line != "" && isGameDir(c) {
			return c, nil
		}
	}
	return "", errors.New("папка игры не найдена (нужна папка, где лежит PWAAT_Data)")
}

func loadConfig() (string, []string, error) {
	path := filepath.Join(exeDir(), configName)
	b, err := os.ReadFile(path)
	if err != nil {
		os.WriteFile(path, []byte(defaultConf), 0o644)
		b = []byte(defaultConf)
	}
	var source string
	var targets []string
	for _, line := range strings.Split(strings.TrimPrefix(string(b), "\ufeff"), "\n") {
		if i := strings.Index(line, "#"); i >= 0 {
			line = line[:i]
		}
		k, v, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		v = strings.TrimSuffix(strings.TrimSpace(v), ".unity3d")
		switch strings.ToLower(strings.TrimSpace(k)) {
		case "source":
			source = v
		case "target":
			if v != "" && !strings.ContainsAny(v, "x?") {
				targets = append(targets, v)
			}
		}
	}
	if source == "" || len(targets) == 0 {
		return "", nil, fmt.Errorf("в %s не заданы source/target", configName)
	}
	return source, targets, nil
}

// original возвращает оригинальный (немодифицированный) файл трека.
func original(bgm, backup, name string) ([]byte, error) {
	if b, err := os.ReadFile(filepath.Join(backup, name+".unity3d")); err == nil {
		return b, nil
	}
	return os.ReadFile(filepath.Join(bgm, name+".unity3d"))
}

func openBundle(raw []byte) (*bundle, []*audioClip, error) {
	dec, err := decrypt(raw)
	if err != nil {
		return nil, nil, err
	}
	b, err := parseBundle(dec)
	if err != nil {
		return nil, nil, err
	}
	clips, err := findClips(b)
	return b, clips, err
}

func install(bgm, backup, source string, targets []string) error {
	raw, err := original(bgm, backup, source)
	if err != nil {
		return fmt.Errorf("не найден исходный трек %s: %w", source, err)
	}
	sb, sclips, err := openBundle(raw)
	if err != nil {
		return fmt.Errorf("%s: %w", source, err)
	}
	src := sclips[0]
	fmt.Printf("\nИсточник: %s  [%s, %.1f сек]\n", source, src.Name(), src.Length())

	if err := os.MkdirAll(backup, 0o755); err != nil {
		return err
	}
	ok := 0
	for _, t := range targets {
		if t == source {
			continue
		}
		path := filepath.Join(bgm, t+".unity3d")
		bpath := filepath.Join(backup, t+".unity3d")
		if _, err := os.Stat(bpath); err != nil {
			cur, err := os.ReadFile(path)
			if err != nil {
				fmt.Printf("  [пропуск] %s: файл не найден\n", t)
				continue
			}
			if err := os.WriteFile(bpath, cur, 0o644); err != nil {
				return fmt.Errorf("не удалось сделать бэкап %s: %w", t, err)
			}
		}
		traw, _ := os.ReadFile(bpath)
		tb, tclips, err := openBundle(traw)
		if err != nil {
			fmt.Printf("  [пропуск] %s: %v\n", t, err)
			continue
		}
		dst := tclips[0]
		oldName, oldLen := dst.Name(), dst.Length()
		if err := replaceAudio(tb, dst, sb, src, len(tclips)); err != nil {
			fmt.Printf("  [пропуск] %s: %v\n", t, err)
			continue
		}
		out := tb.serialize()
		// Самопроверка: результат должен читаться обратно.
		if _, c2, err := openBundle(encrypt(out)); err != nil || c2[0].Size() != src.Size() {
			fmt.Printf("  [пропуск] %s: самопроверка не прошла (%v)\n", t, err)
			continue
		}
		if err := os.WriteFile(path, encrypt(out), 0o644); err != nil {
			return fmt.Errorf("не удалось записать %s: %w", t, err)
		}
		fmt.Printf("  [OK] %s  [%s, %.1f сек]  ->  Objection! 2001\n", t, oldName, oldLen)
		ok++
	}
	if ok == 0 {
		return errors.New("ни один трек не заменён")
	}
	return nil
}

func restore(bgm, backup string) error {
	files, _ := filepath.Glob(filepath.Join(backup, "*.unity3d"))
	if len(files) == 0 {
		fmt.Println("Бэкапов нет — мод не установлен.")
		return nil
	}
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		if err := os.WriteFile(filepath.Join(bgm, filepath.Base(f)), b, 0o644); err != nil {
			return err
		}
		os.Remove(f)
		fmt.Println("  [восстановлен]", filepath.Base(f))
	}
	os.Remove(backup)
	fmt.Println("\nМод удалён, оригинальная музыка возвращена.")
	return nil
}

func writeList(bgm, backup, out string) error {
	files, _ := filepath.Glob(filepath.Join(bgm, "*.unity3d"))
	sort.Strings(files)
	var sb strings.Builder
	sb.WriteString("Список музыкальных файлов (оригиналы). Формат: файл | имя клипа | длина\n\n")
	for _, f := range files {
		name := strings.TrimSuffix(filepath.Base(f), ".unity3d")
		raw, err := original(bgm, backup, name)
		if err != nil {
			continue
		}
		_, clips, err := openBundle(raw)
		if err != nil {
			fmt.Fprintf(&sb, "%-10s | ошибка: %v\n", name, err)
			continue
		}
		c := clips[0]
		fmt.Fprintf(&sb, "%-10s | %-24s | %d:%04.1f\n", name, c.Name(), int(c.Length())/60,
			float64(c.Length())-float64(int(c.Length())/60*60))
	}
	if err := os.WriteFile(out, []byte("\ufeff"+sb.String()), 0o644); err != nil {
		return err
	}
	fmt.Println("Список треков сохранён:", out)
	return nil
}

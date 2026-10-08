package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestCryptoRoundtrip(t *testing.T) {
	in := []byte("UnityFS\x00some bundle data")
	enc := encrypt(in)
	if !isEncrypted(enc) {
		t.Fatal("not encrypted")
	}
	dec, err := decrypt(enc)
	if err != nil || !bytes.Equal(dec, in) {
		t.Fatalf("roundtrip failed: %v", err)
	}
}

// Реальные бандлы: parse -> serialize -> parse должен дать те же узлы.
// Каталог задаётся переменной SAMPLES; без неё тест пропускается.
func TestRealBundlesRoundtrip(t *testing.T) {
	dir := os.Getenv("SAMPLES")
	if dir == "" {
		t.Skip("SAMPLES not set")
	}
	files, _ := filepath.Glob(filepath.Join(dir, "*"))
	for _, f := range files {
		raw, _ := os.ReadFile(f)
		b, err := parseBundle(raw)
		if err != nil {
			t.Fatalf("%s: %v", f, err)
		}
		out := b.serialize()
		b2, err := parseBundle(out)
		if err != nil {
			t.Fatalf("%s reparse: %v", f, err)
		}
		for i, n := range b.Nodes {
			if b2.Nodes[i].Path != n.Path || !bytes.Equal(b2.Nodes[i].Data, n.Data) {
				t.Fatalf("%s node %d differs", f, i)
			}
		}
		os.WriteFile(f+".out", out, 0o644)
		t.Logf("%s: format %d, %s, flags %#x, %d nodes OK", filepath.Base(f), b.Format, b.Version, b.Flags, len(b.Nodes))
	}
}

// fakeClipBundle строит бандл с объектом AudioClip в раскладке Unity 2017.
func fakeClipBundle(cab, name string, ch, freq uint32, length float32, audio []byte) *bundle {
	le := binary.LittleEndian
	var d bytes.Buffer
	d.Write(make([]byte, 64)) // «заголовок» сериализованного файла, endianness=0
	str := func(s string) {
		binary.Write(&d, le, uint32(len(s)))
		d.WriteString(s)
		for d.Len()%4 != 0 {
			d.WriteByte(0)
		}
	}
	str(name)
	for _, v := range []uint32{1, ch, freq, 16, math.Float32bits(length)} {
		binary.Write(&d, le, v)
	}
	d.Write([]byte{0, 0, 0, 0}) // tracker, ambisonic
	binary.Write(&d, le, uint32(0))
	d.Write([]byte{0, 1, 0, 0}) // preload, bg, legacy3d
	str("archive:/" + cab + "/" + cab + ".resource")
	binary.Write(&d, le, uint64(0))
	binary.Write(&d, le, uint64(len(audio)))
	binary.Write(&d, le, uint32(1))
	d.Write(make([]byte, 40))
	return &bundle{Format: 6, Version: "5.x.x", Revision: "2017.4.40f1", Flags: 0x43,
		Nodes: []*node{{Flags: 4, Path: cab, Data: d.Bytes()}, {Flags: 0, Path: cab + ".resource", Data: audio}}}
}

func TestReplaceAudio(t *testing.T) {
	dir := t.TempDir()
	bgm := filepath.Join(dir, "bgm")
	backup := filepath.Join(dir, "bak")
	os.MkdirAll(bgm, 0o755)
	srcAudio := bytes.Repeat([]byte("FSB5-objection-2001!"), 50000)
	src := fakeClipBundle("CAB-src", "bgm012", 2, 44100, 81.5, srcAudio)
	dst := fakeClipBundle("CAB-dst", "bgm121", 1, 32000, 60.25, bytes.Repeat([]byte("old"), 1000))
	os.WriteFile(filepath.Join(bgm, "bgm012.unity3d"), encrypt(src.serialize()), 0o644)
	os.WriteFile(filepath.Join(bgm, "bgm121.unity3d"), encrypt(dst.serialize()), 0o644)
	origDst, _ := os.ReadFile(filepath.Join(bgm, "bgm121.unity3d"))

	if err := install(bgm, backup, "bgm012", []string{"bgm121"}); err != nil {
		t.Fatal(err)
	}
	// повторная установка не должна портить бэкап
	if err := install(bgm, backup, "bgm012", []string{"bgm121"}); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(filepath.Join(bgm, "bgm121.unity3d"))
	b, clips, err := openBundle(raw)
	if err != nil {
		t.Fatal(err)
	}
	c := clips[0]
	if c.Name() != "bgm121" || c.Channels() != 2 || c.Frequency() != 44100 || c.Length() != 81.5 {
		t.Fatalf("fields: %s %d %d %v", c.Name(), c.Channels(), c.Frequency(), c.Length())
	}
	if c.ResourceName() != "CAB-dst.resource" {
		t.Fatal("source string changed")
	}
	got, err := c.resourceData(b)
	if err != nil || !bytes.Equal(got, srcAudio) {
		t.Fatal("audio not replaced")
	}

	if err := restore(bgm, backup); err != nil {
		t.Fatal(err)
	}
	now, _ := os.ReadFile(filepath.Join(bgm, "bgm121.unity3d"))
	if !bytes.Equal(now, origDst) {
		t.Fatal("restore failed")
	}
}

// Настоящий бандл с несколькими AudioClip: подменяем звук первого клипа звуком
// последнего и сохраняем результат для проверки через UnityPy.
func TestRealAudioClipReplace(t *testing.T) {
	dir := os.Getenv("SAMPLES")
	if dir == "" {
		t.Skip("SAMPLES not set")
	}
	raw, err := os.ReadFile(filepath.Join(dir, "char_118_yuki.ab"))
	if err != nil {
		t.Skip(err)
	}
	b, clips, err := openBundle(raw)
	if err != nil {
		t.Fatal(err)
	}
	for _, c := range clips {
		t.Logf("%s ch=%d fr=%d len=%.2f off=%d size=%d", c.Name(), c.Channels(), c.Frequency(), c.Length(), c.Offset(), c.Size())
	}
	sb, sclips, _ := openBundle(raw)
	src := sclips[len(sclips)-1]
	if err := replaceAudio(b, clips[0], sb, src, len(clips)); err != nil {
		t.Fatal(err)
	}
	os.WriteFile(filepath.Join(dir, "replaced.ab"), b.serialize(), 0o644)
}

func TestProbe(t *testing.T) {
	dir := t.TempDir()
	bgm := filepath.Join(dir, "bgm")
	os.MkdirAll(bgm, 0o755)
	for i := 0; i < 15; i++ {
		n := fmt.Sprintf("bgm%03d", i)
		b := fakeClipBundle("CAB-"+n, n, 2, 44100, 50+float32(i)*3, []byte(n))
		os.WriteFile(filepath.Join(bgm, n+".unity3d"), encrypt(b.serialize()), 0o644)
	}
	for _, pt := range probeTargets {
		b := fakeClipBundle("CAB-"+pt.file, pt.file, 2, 44100, 60, []byte("tt"))
		os.WriteFile(filepath.Join(bgm, pt.file+".unity3d"), encrypt(b.serialize()), 0o644)
	}
	if err := probe(bgm, filepath.Join(dir, "bak"), 1); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(filepath.Join(bgm, "bgm117.unity3d"))
	b, clips, _ := openBundle(raw)
	got, _ := clips[0].resourceData(b)
	if string(got) != "bgm008" { // ближайший к 75 сек (50+8*3=74)
		t.Fatalf("bgm117 got %q", got)
	}
}

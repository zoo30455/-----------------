package main

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"io"

	"github.com/pierrec/lz4/v4"
	"github.com/ulikunitz/xz/lzma"
)

// Минимальная реализация формата UnityFS (чтение + запись).

type node struct {
	Flags uint32
	Path  string
	Data  []byte
}

type bundle struct {
	Format   uint32
	Version  string
	Revision string
	Flags    uint32
	Hash     [16]byte
	Nodes    []*node
}

const (
	flagCompressionMask = 0x3F
	flagBlocksInfoAtEnd = 0x80
	flagPaddingAtStart  = 0x200
	lz4ChunkSize        = 0x20000
)

func decompress(kind uint32, src []byte, size uint32) ([]byte, error) {
	switch kind {
	case 0:
		return src, nil
	case 1: // LZMA: 5 байт свойств + сырой поток
		if len(src) < 5 {
			return nil, errors.New("битый LZMA блок")
		}
		hdr := make([]byte, 13)
		copy(hdr, src[:5])
		binary.LittleEndian.PutUint64(hdr[5:], uint64(size))
		r, err := lzma.NewReader(io.MultiReader(bytes.NewReader(hdr), bytes.NewReader(src[5:])))
		if err != nil {
			return nil, err
		}
		out := make([]byte, size)
		_, err = io.ReadFull(r, out)
		return out, err
	case 2, 3: // LZ4 / LZ4HC
		out := make([]byte, size)
		n, err := lz4.UncompressBlock(src, out)
		if err != nil {
			return nil, err
		}
		if n != int(size) {
			return nil, errors.New("LZ4: неверный размер")
		}
		return out, nil
	}
	return nil, fmt.Errorf("неизвестный тип сжатия %d", kind)
}

type reader struct {
	b   []byte
	pos int
	err error
}

func (r *reader) need(n int) bool {
	if r.err == nil && r.pos+n > len(r.b) {
		r.err = io.ErrUnexpectedEOF
	}
	return r.err == nil
}
func (r *reader) bytes(n int) []byte {
	if !r.need(n) {
		return make([]byte, n)
	}
	v := r.b[r.pos : r.pos+n]
	r.pos += n
	return v
}
func (r *reader) u16() uint16 { return binary.BigEndian.Uint16(r.bytes(2)) }
func (r *reader) u32() uint32 { return binary.BigEndian.Uint32(r.bytes(4)) }
func (r *reader) u64() uint64 { return binary.BigEndian.Uint64(r.bytes(8)) }
func (r *reader) cstr() string {
	i := bytes.IndexByte(r.b[r.pos:], 0)
	if i < 0 {
		r.err = io.ErrUnexpectedEOF
		return ""
	}
	s := string(r.b[r.pos : r.pos+i])
	r.pos += i + 1
	return s
}
func (r *reader) align(n int) {
	if m := r.pos % n; m != 0 {
		r.pos += n - m
	}
}

func parseBundle(data []byte) (*bundle, error) {
	r := &reader{b: data}
	if r.cstr() != "UnityFS" {
		return nil, errors.New("не UnityFS бандл")
	}
	b := &bundle{}
	b.Format = r.u32()
	b.Version = r.cstr()
	b.Revision = r.cstr()
	r.u64() // общий размер
	compSize := r.u32()
	uncompSize := r.u32()
	b.Flags = r.u32()
	if b.Format >= 7 {
		r.align(16)
	}
	var infoRaw []byte
	if b.Flags&flagBlocksInfoAtEnd != 0 {
		if int(compSize) > len(data) {
			return nil, io.ErrUnexpectedEOF
		}
		infoRaw = data[len(data)-int(compSize):]
	} else {
		infoRaw = r.bytes(int(compSize))
	}
	if r.err != nil {
		return nil, r.err
	}
	info, err := decompress(b.Flags&flagCompressionMask, infoRaw, uncompSize)
	if err != nil {
		return nil, fmt.Errorf("blocksInfo: %w", err)
	}
	if b.Flags&flagPaddingAtStart != 0 {
		r.align(16)
	}

	ir := &reader{b: info}
	copy(b.Hash[:], ir.bytes(16))
	type blk struct {
		u, c  uint32
		flags uint16
	}
	blocks := make([]blk, ir.u32())
	for i := range blocks {
		blocks[i] = blk{ir.u32(), ir.u32(), ir.u16()}
	}
	nodeCount := ir.u32()
	type nodeInfo struct {
		off, size uint64
		flags     uint32
		path      string
	}
	infos := make([]nodeInfo, 0, nodeCount)
	for i := uint32(0); i < nodeCount && ir.err == nil; i++ {
		infos = append(infos, nodeInfo{ir.u64(), ir.u64(), ir.u32(), ir.cstr()})
	}
	if ir.err != nil {
		return nil, fmt.Errorf("blocksInfo: %w", ir.err)
	}

	var stream bytes.Buffer
	for _, bl := range blocks {
		raw := r.bytes(int(bl.c))
		if r.err != nil {
			return nil, r.err
		}
		d, err := decompress(uint32(bl.flags)&flagCompressionMask, raw, bl.u)
		if err != nil {
			return nil, fmt.Errorf("блок данных: %w", err)
		}
		stream.Write(d)
	}
	all := stream.Bytes()
	for _, ni := range infos {
		if ni.off+ni.size > uint64(len(all)) {
			return nil, errors.New("узел выходит за пределы данных")
		}
		b.Nodes = append(b.Nodes, &node{Flags: ni.flags, Path: ni.path, Data: all[ni.off : ni.off+ni.size]})
	}
	return b, nil
}

func (b *bundle) node(path string) *node {
	for _, n := range b.Nodes {
		if n.Path == path {
			return n
		}
	}
	return nil
}

// serialize пишет бандл с LZ4-сжатием данных кусками по 128 КБ (как делает Unity)
// и несжатым blocksInfo сразу после заголовка.
func (b *bundle) serialize() []byte {
	var all bytes.Buffer
	var info bytes.Buffer
	be := binary.BigEndian
	info.Write(b.Hash[:])

	type nodeInfo struct{ off, size uint64 }
	nis := make([]nodeInfo, len(b.Nodes))
	for i, n := range b.Nodes {
		nis[i] = nodeInfo{uint64(all.Len()), uint64(len(n.Data))}
		all.Write(n.Data)
	}

	var blocksData bytes.Buffer
	var blockHdrs bytes.Buffer
	nBlocks := 0
	src := all.Bytes()
	for off := 0; off < len(src) || (off == 0 && len(src) == 0); off += lz4ChunkSize {
		end := off + lz4ChunkSize
		if end > len(src) {
			end = len(src)
		}
		chunk := src[off:end]
		dst := make([]byte, lz4.CompressBlockBound(len(chunk)))
		var c lz4.Compressor
		n, err := c.CompressBlock(chunk, dst)
		flags := uint16(2)
		out := dst[:n]
		if err != nil || n == 0 || n >= len(chunk) {
			flags, out = 0, chunk
		}
		binary.Write(&blockHdrs, be, uint32(len(chunk)))
		binary.Write(&blockHdrs, be, uint32(len(out)))
		binary.Write(&blockHdrs, be, flags)
		blocksData.Write(out)
		nBlocks++
		if len(src) == 0 {
			break
		}
	}
	binary.Write(&info, be, uint32(nBlocks))
	info.Write(blockHdrs.Bytes())
	binary.Write(&info, be, uint32(len(b.Nodes)))
	for i, n := range b.Nodes {
		binary.Write(&info, be, nis[i].off)
		binary.Write(&info, be, nis[i].size)
		binary.Write(&info, be, n.Flags)
		info.WriteString(n.Path)
		info.WriteByte(0)
	}

	flags := b.Flags &^ (flagCompressionMask | flagBlocksInfoAtEnd)
	var hdr bytes.Buffer
	hdr.WriteString("UnityFS\x00")
	binary.Write(&hdr, be, b.Format)
	hdr.WriteString(b.Version + "\x00")
	hdr.WriteString(b.Revision + "\x00")
	sizePos := hdr.Len()
	binary.Write(&hdr, be, uint64(0))
	binary.Write(&hdr, be, uint32(info.Len()))
	binary.Write(&hdr, be, uint32(info.Len()))
	binary.Write(&hdr, be, flags)
	pad16 := func() {
		for hdr.Len()%16 != 0 {
			hdr.WriteByte(0)
		}
	}
	if b.Format >= 7 {
		pad16()
	}
	hdr.Write(info.Bytes())
	if flags&flagPaddingAtStart != 0 {
		pad16()
	}
	hdr.Write(blocksData.Bytes())
	out := hdr.Bytes()
	be.PutUint64(out[sizePos:], uint64(len(out)))
	return out
}

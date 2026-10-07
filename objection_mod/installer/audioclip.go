package main

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"math"
	"strings"
)

// audioClip указывает на поля объекта AudioClip внутри сериализованного файла
// бандла. Раскладка полей (Unity 5.x–2019):
//
//	m_Name, m_LoadType, m_Channels, m_Frequency, m_BitsPerSample, m_Length,
//	m_IsTrackerFormat, m_Ambisonic, (align) m_SubsoundIndex,
//	m_PreloadAudioData, m_LoadInBackground, m_Legacy3D, (align)
//	m_Resource { m_Source, (align) m_Offset u64, m_Size u64 }, m_CompressionFormat
//
// Объект находим по строке m_Source ("archive:/CAB-.../CAB-....resource").
type audioClip struct {
	file   *node
	bo     binary.ByteOrder
	lenPos int // позиция длины строки m_Source
	resPos int // позиция m_Offset
	Source string
}

func (c *audioClip) field(off int) []byte { return c.file.Data[c.lenPos+off:] }

func (c *audioClip) Channels() uint32   { return c.bo.Uint32(c.field(-28)) }
func (c *audioClip) Frequency() uint32  { return c.bo.Uint32(c.field(-24)) }
func (c *audioClip) Length() float32    { return math.Float32frombits(c.bo.Uint32(c.field(-16))) }
func (c *audioClip) Offset() uint64     { return c.bo.Uint64(c.file.Data[c.resPos:]) }
func (c *audioClip) Size() uint64       { return c.bo.Uint64(c.file.Data[c.resPos+8:]) }
func (c *audioClip) ResourceName() string {
	return c.Source[strings.LastIndex(c.Source, "/")+1:]
}

// Name пытается прочитать m_Name: ищем назад строку, длина которой совпадает.
func (c *audioClip) Name() string {
	d := c.file.Data
	end := c.lenPos - 32 // начало m_LoadType
	for l := 0; l <= 256; l++ {
		p := end - ((l + 3) &^ 3) - 4
		if p < 0 {
			break
		}
		if int(c.bo.Uint32(d[p:])) == l {
			s := d[p+4 : p+4+l]
			if isPrintable(s) {
				return string(s)
			}
		}
	}
	return "?"
}

func isPrintable(s []byte) bool {
	for _, ch := range s {
		if ch < 0x20 || ch > 0x7E {
			return false
		}
	}
	return true
}

func serializedByteOrder(d []byte) binary.ByteOrder {
	if len(d) > 16 && d[16] != 0 {
		return binary.BigEndian
	}
	return binary.LittleEndian
}

func findClips(b *bundle) ([]*audioClip, error) {
	var clips []*audioClip
	marker := []byte("archive:/")
	for _, n := range b.Nodes {
		if strings.HasSuffix(n.Path, ".resS") || strings.HasSuffix(n.Path, ".resource") {
			continue
		}
		bo := serializedByteOrder(n.Data)
		d := n.Data
		for start := 0; ; {
			i := bytes.Index(d[start:], marker)
			if i < 0 {
				break
			}
			pos := start + i
			start = pos + 1
			if pos < 36 {
				continue
			}
			l := int(bo.Uint32(d[pos-4:]))
			if l < len(marker) || pos+l > len(d) || !isPrintable(d[pos:pos+l]) {
				continue
			}
			resPos := (pos + l + 3) &^ 3
			if resPos+16 > len(d) {
				continue
			}
			c := &audioClip{file: n, bo: bo, lenPos: pos - 4, resPos: resPos, Source: string(d[pos : pos+l])}
			if ch, fr := c.Channels(), c.Frequency(); ch < 1 || ch > 8 || fr < 8000 || fr > 192000 {
				continue
			}
			clips = append(clips, c)
		}
	}
	if len(clips) == 0 {
		return nil, errors.New("AudioClip не найден в бандле")
	}
	return clips, nil
}

func (c *audioClip) resourceData(b *bundle) ([]byte, error) {
	rn := b.node(c.ResourceName())
	if rn == nil {
		return nil, fmt.Errorf("в бандле нет ресурса %s", c.ResourceName())
	}
	off, size := c.Offset(), c.Size()
	if off+size > uint64(len(rn.Data)) {
		return nil, errors.New("AudioClip указывает за пределы ресурса")
	}
	return rn.Data[off : off+size], nil
}

// replaceAudio подменяет звук клипа dst (в бандле tb) звуком клипа src (из sb).
func replaceAudio(tb *bundle, dst *audioClip, sb *bundle, src *audioClip, clipsInTarget int) error {
	audio, err := src.resourceData(sb)
	if err != nil {
		return err
	}
	rn := tb.node(dst.ResourceName())
	if rn == nil {
		return fmt.Errorf("в целевом бандле нет ресурса %s", dst.ResourceName())
	}
	var newOff uint64
	if clipsInTarget == 1 {
		rn.Data = append([]byte(nil), audio...)
	} else {
		// В ресурсе несколько клипов: дописываем звук в конец, не трогая остальные.
		data := append([]byte(nil), rn.Data...)
		for len(data)%32 != 0 {
			data = append(data, 0)
		}
		newOff = uint64(len(data))
		rn.Data = append(data, audio...)
	}
	// Копируем параметры звука: m_Channels..m_Length, m_SubsoundIndex,
	// затем m_Offset/m_Size и m_CompressionFormat.
	d := dst.file.Data
	copy(d[dst.lenPos-28:dst.lenPos-12], src.file.Data[src.lenPos-28:src.lenPos-12])
	copy(d[dst.lenPos-8:dst.lenPos-4], src.file.Data[src.lenPos-8:src.lenPos-4])
	dst.bo.PutUint64(d[dst.resPos:], newOff)
	dst.bo.PutUint64(d[dst.resPos+8:], uint64(len(audio)))
	if dst.resPos+20 <= len(d) && src.resPos+20 <= len(src.file.Data) {
		copy(d[dst.resPos+16:dst.resPos+20], src.file.Data[src.resPos+16:src.resPos+20])
	}
	return nil
}

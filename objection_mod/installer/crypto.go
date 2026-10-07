package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/binary"
	"errors"
)

// Ключ шифрования ассетов PWAAT (см. Kaplas80/PhoenixWrightTrilogyTools):
// AES-128-CBC, ключ и IV из PBKDF2-SHA1(password, salt, 1000 итераций).
const (
	gamePassword = "u8DurGE2"
	gameSalt     = "6BBGizHE"
)

var gameKey, gameIV = deriveKeyIV()

func pbkdf2SHA1(password, salt []byte, iter, keyLen int) []byte {
	prf := hmac.New(sha1.New, password)
	var out []byte
	for block := uint32(1); len(out) < keyLen; block++ {
		prf.Reset()
		prf.Write(salt)
		var b [4]byte
		binary.BigEndian.PutUint32(b[:], block)
		prf.Write(b[:])
		u := prf.Sum(nil)
		t := append([]byte(nil), u...)
		for i := 1; i < iter; i++ {
			prf.Reset()
			prf.Write(u)
			u = prf.Sum(nil)
			for j := range t {
				t[j] ^= u[j]
			}
		}
		out = append(out, t...)
	}
	return out[:keyLen]
}

func deriveKeyIV() ([]byte, []byte) {
	k := pbkdf2SHA1([]byte(gamePassword), []byte(gameSalt), 1000, 32)
	return k[:16], k[16:32]
}

func isEncrypted(data []byte) bool {
	return !bytes.HasPrefix(data, []byte("UnityFS"))
}

func decrypt(data []byte) ([]byte, error) {
	if !isEncrypted(data) {
		return data, nil
	}
	if len(data) == 0 || len(data)%aes.BlockSize != 0 {
		return nil, errors.New("неверный размер зашифрованного файла")
	}
	block, _ := aes.NewCipher(gameKey)
	out := make([]byte, len(data))
	cipher.NewCBCDecrypter(block, gameIV).CryptBlocks(out, data)
	pad := int(out[len(out)-1])
	if pad < 1 || pad > aes.BlockSize {
		return nil, errors.New("не удалось расшифровать файл (неверный padding)")
	}
	out = out[:len(out)-pad]
	if isEncrypted(out) {
		return nil, errors.New("после расшифровки это не UnityFS")
	}
	return out, nil
}

func encrypt(data []byte) []byte {
	pad := aes.BlockSize - len(data)%aes.BlockSize
	in := make([]byte, len(data)+pad)
	copy(in, data)
	for i := len(data); i < len(in); i++ {
		in[i] = byte(pad)
	}
	block, _ := aes.NewCipher(gameKey)
	cipher.NewCBCEncrypter(block, gameIV).CryptBlocks(in, in)
	return in
}

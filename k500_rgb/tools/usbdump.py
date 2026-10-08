import struct, sys
from pcapng import FileScanner
from pcapng.blocks import EnhancedPacket

def packets(path):
    with open(path, 'rb') as f:
        t0 = None
        for b in FileScanner(f):
            if not isinstance(b, EnhancedPacket):
                continue
            d = b.packet_data
            hl, irp, st, fn, info, bus, dev, ep, tt, dl = struct.unpack_from('<HQIHBHHBBI', d, 0)
            ts = b.timestamp
            t0 = t0 if t0 is not None else ts
            payload = d[hl:]
            yield ts - t0, info & 1, ep, tt, payload

def main():
  for path in sys.argv[1:]:
    print('#', path)
    for ts, resp, ep, tt, p in packets(path):
        if resp or not p:
            continue
        if tt == 2:  # control setup stage: 8-byte setup + data
            setup, data = p[:8], p[8:]
            if setup[1] != 0x09:  # SET_REPORT only
                continue
            print(f'{ts:9.3f} CTRL  wValue={setup[3]:02x}{setup[2]:02x} wIndex={setup[4]} {data.hex(" ")}')
        elif tt == 1 and (ep & 0x80) == 0:
            print(f'{ts:9.3f} OUT{ep:02x} {p.hex(" ")}')

if __name__ == '__main__':
    main()

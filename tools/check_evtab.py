# -*- coding: utf-8 -*-
r"""빌드 이미지 검산(2026-11-26 새 게임 크래시 뒤): EVE_TM·EVE_MAIN 의 EVENT 덩어리 위치표가 새 EVENT.BIN 과 맞는지
  python tools/check_evtab.py dist/build/disc1/...(Track 1).bin [디스크번호]
  기준: 원본 위치표의 각 덩어리 내용(첫 32 B·이름)이 새 표가 가리키는 자리에서도 같은 순서로 이어지는지 + 표 끝이 파일 안"""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import iso
sys.stdout.reconfigure(encoding='utf-8')
img = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
orig = iso.Disc(n); iso.ROMS[n] = img; new = iso.Disc(n)
def rd(D, name):
    F = {p.strip('/'): (l, s) for p, l, s in D.files}; l, s = F[name]; return D.sec(l, (s + 2047) // 2048)[:s]
oev, nev = rd(orig, 'EVENT.BIN'), rd(new, 'EVENT.BIN')
bad = 0
for mod, T in (('EVE_TM.BIN', 0x1CB50), ('EVE_MAIN.BIN', 0x24470)):
    om, nm = rd(orig, mod), rd(new, mod)
    for k in range(34):
        a = T + 24 * k
        oo, os_ = struct.unpack('>II', om[a:a + 8]); no, ns = struct.unpack('>II', nm[a:a + 8])
        if om[a + 8:a + 24] != nm[a + 8:a + 24]: print('이름 다름', mod, k); bad += 1
        if no + ns > len(nev) or ns > 0x10800: print('범위 밖', mod, k, hex(no), ns); bad += 1; continue
        if os_ and nev[no:no + 8] != oev[oo:oo + 8]: print('머리 다름', mod, k, oev[oo:oo + 8].hex(), nev[no:no + 8].hex()); bad += 1
print('위치표 검산:', '통과' if not bad else '⛔ %d' % bad)
sys.exit(1 if bad else 0)

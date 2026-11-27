# -*- coding: utf-8 -*-
"""EVE 글 영역을 글꼴(A_FONT16, 16x16 1bpp)로 그려 본다.
코드: 2바이트 110xxxxx 10xxxxxx → 11비트 값 = 글꼴 칸 (대사 스테이트 RAM 으로 확인) / 0xFF xx = 제어(새 줄로 표시)
python tools/render_codes.py <파일> <시작hex> <끝hex> <출력png>"""
import sys
from PIL import Image
OFF = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0
F = open('work/disc1/A_FONT16.BIN', 'rb').read()
d = open(sys.argv[1], 'rb').read(); a, b = int(sys.argv[2], 16), int(sys.argv[3], 16)
lines = [[]]; i = a
while i < b:
    c = d[i]
    if c == 0xFF: lines[-1].append(('ctl', d[i + 1])); lines.append([]); i += 2
    elif 0xC0 <= c < 0xE0 and 0x80 <= d[i + 1] < 0xC0:
        lines[-1].append(('g', (((c & 0x1F) << 6) | (d[i + 1] & 0x3F)) - OFF)); i += 2
    else: lines[-1].append(('x', c)); i += 1
W = max(len(l) for l in lines) * 17; im = Image.new('L', (W, len(lines) * 18), 0); px = im.load()
for y, l in enumerate(lines):
    for x, (k, v) in enumerate(l):
        if k == 'g' and 0 <= v < 2048:
            for r in range(16):
                w = F[v * 32 + r * 2] << 8 | F[v * 32 + r * 2 + 1]
                for c in range(16):
                    if w >> (15 - c) & 1: px[x * 17 + c, y * 18 + r] = 255
        else:
            for r in range(16): px[x * 17 + 8, y * 18 + r] = 90 if k == 'ctl' else 160
im.save(sys.argv[4]); print(len(lines), 'lines')

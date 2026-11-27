# -*- coding: utf-8 -*-
"""디스크 파일 전체에서 2바이트 글 조각 찾기 — 조각 = 연속 코드 2개 이상, 가나(0x1A1~0x257) 1개 이상 포함, 빈 글리프 없음.
python tools/scan_text.py [disc1|disc2] → 파일별 조각 수·글자 수"""
import glob, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
F = np.frombuffer(open(os.path.join(ROOT, 'work', 'disc1', 'A_FONT16.BIN'), 'rb').read(), np.uint8).reshape(2048, 32)
EMPTY = set(np.nonzero(F.sum(1) == 0)[0].tolist())


def pieces(d, kana=True):
    out = []; cur = []; st = 0; i = 0
    while i < len(d) - 1:
        b = d[i]
        if 0xC0 <= b < 0xE0 and 0x80 <= d[i + 1] < 0xC0:
            if not cur: st = i
            cur.append(((b & 0x1F) << 6) | (d[i + 1] & 0x3F)); i += 2; continue
        if len(cur) >= 2 and (not kana or any(0x1A1 <= c < 0x258 for c in cur)) and not any(c in EMPTY for c in cur):
            out.append((st, cur))
        cur = []; i += 1
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    disc = sys.argv[1] if len(sys.argv) > 1 else 'disc1'
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', disc, '*'))):
        if f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        p = pieces(open(f, 'rb').read())
        if len(p) >= 10: print('%-14s %6d조각 %8d자' % (os.path.basename(f), len(p), sum(len(c) for _, c in p)))

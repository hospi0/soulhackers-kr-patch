# -*- coding: utf-8 -*-
"""가나 문장을 «상대 코드 간격»으로 검색(인코딩 모를 때). 히라가나 JIS 순서 가정.
python tools/relsearch.py "<glob>" 문장1 문장2 ..."""
import glob, os, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
H = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん'


def find(a, r):
    n = len(r)
    if len(a) < n + 1: return np.array([], int)
    L = len(a) - n + 1; m = np.ones(L, bool)
    for j in range(1, n): m &= (a[j:L + j] - a[:L]) == (r[j] - r[0])
    return np.nonzero(m)[0]


for f in sorted(glob.glob(sys.argv[1])):
    if os.path.getsize(f) < 64: continue
    d = open(f, 'rb').read()
    for p in sys.argv[2:]:
        r = [H.index(c) for c in p]
        for fmt in ('>', '<'):
            for off in (0, 1):
                a = np.frombuffer(d[off:off + (len(d) - off) // 2 * 2], dtype=fmt + 'u2').astype(int)
                idx = find(a, r)
                if 0 < len(idx) < 200: print(f, p, fmt, off, len(idx), [hex(off + 2 * i) for i in idx[:3]], 'base', hex(a[idx[0]] - r[0]))
        a = np.frombuffer(d, dtype='u1').astype(int); idx = find(a, r)
        if 0 < len(idx) < 50: print(f, p, 'u8', len(idx), [hex(i) for i in idx[:3]], 'base', hex(a[idx[0]] - r[0]))

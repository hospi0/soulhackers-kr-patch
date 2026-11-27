# -*- coding: utf-8 -*-
"""글 구역 찾기 — 조각 사이 틈이 GAP 바이트 이하면 한 구역. 구역 점수 = 조각 글다움 중간값.
python tools/text_regions.py [파일...] → work/text_regions.tsv (파일 · 시작 · 끝 · 조각 · 글자 · 중간점수)"""
import glob, os, sys, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import scan_text, textscore
D1 = os.path.join(ROOT, 'work', 'disc1'); GAP = 24


def regions(d, sc):
    P = scan_text.pieces(d); R = []
    for st, c in P:
        en = st + 2 * len(c)
        if R and st - R[-1][1] <= GAP: R[-1][1] = en; R[-1][2].append(c)
        else: R.append([st, en, [c]])
    return [(a, b, cs, statistics.median(sc(c) for c in cs)) for a, b, cs in R]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sc = textscore.model()
    fs = sys.argv[1:] or [os.path.basename(f) for f in sorted(glob.glob(os.path.join(D1, '*'))) if not f.endswith(('.AVI', '.AIF')) and os.path.getsize(f) <= 30_000_000]
    out = ['파일\t시작\t끝\t조각\t글자\t중간점수']
    for f in fs:
        for a, b, cs, m in regions(open(os.path.join(D1, f), 'rb').read(), sc):
            if len(cs) >= 4: out.append('%s\t%X\t%X\t%d\t%d\t%.2f' % (f, a, b, len(cs), sum(map(len, cs)), m))
    open(os.path.join(ROOT, 'work', 'text_regions.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(len(out) - 1, '구역')

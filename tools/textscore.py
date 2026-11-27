# -*- coding: utf-8 -*-
"""글 조각 «글다움» 점수 — EVENT.BIN·TALK*.EVE 조각으로 만든 글자 바이그램(+1 평활) 평균 로그확률.
python tools/textscore.py → 파일별 «점수 −4.0 이상» 조각 수 (기준은 표본 그림으로 정함)"""
import collections, glob, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import scan_text
D1 = os.path.join(ROOT, 'work', 'disc1')


def model():
    U = collections.Counter(); B = collections.Counter()
    for f in ['EVENT.BIN'] + [os.path.basename(x) for x in glob.glob(os.path.join(D1, 'TALK*.EVE'))]:
        for _, c in scan_text.pieces(open(os.path.join(D1, f), 'rb').read()):
            s = [-1] + c + [-2]
            U.update(s[:-1]); B.update(zip(s, s[1:]))
    V = 2050
    def score(c):
        s = [-1] + c + [-2]
        return sum(math.log((B[(a, b)] + 0.01) / (U[a] + 0.01 * V)) for a, b in zip(s, s[1:])) / (len(s) - 1)
    return score


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sc = model(); TH = float(sys.argv[1]) if len(sys.argv) > 1 else -4.0
    for f in sorted(glob.glob(os.path.join(D1, '*'))):
        if f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        P = scan_text.pieces(open(f, 'rb').read())
        if len(P) < 10: continue
        good = [c for _, c in P if sc(c) >= TH]
        print('%-14s 조각 %6d → 글다움 %6d (%5.1f%%) %8d자' % (os.path.basename(f), len(P), len(good), 100 * len(good) / len(P), sum(map(len, good))))

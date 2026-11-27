# -*- coding: utf-8 -*-
r"""줄임안 검사(2026-11-26) — work/review/줄임안_*.tsv 의 각 줄을 빌더와 같은 순서(부호 뒤 공백·채움·자동 줄바꿈)로 돌려 넘침·바이트·토큰 확인
  python tools/check_props.py work/review/줄임안_1.tsv"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import check_lines as C, build as B, kfont, review as R
sys.stdout.reconfigure(encoding='utf-8')
C.init_vars([])
master, order, tr, bad = R.load()
P = [l.split('\t') for l in open(sys.argv[1], encoding='utf-8').read().splitlines()[1:] if '\t' in l]
_, keep = kfont.tables(); km = kfont.assign({c for _, t in P for c in t if kfont.is_ko(c)}, save=False)
ng = 0
for i, t in P:
    p = master[i][1]; f, ja, n = p[1], p[4], int(p[3]); C.CUR[0] = (f, int(p[2], 16))
    t2 = C.reflow(f, ja, C.fit_fill(ja, C.squeeze(ja, t)))
    ov = C.overflow(f, ja, t2); tok = B.tokens(ja) == B.tokens(t2) or i in B.TOKEN_FREE_ID
    try: nb = len(B.encode(t2, km, keep))
    except B.BuildError as e: nb = 99999
    inplace = not (f == 'EVENT.BIN' or f.endswith('.EVE') or f in B.INDEXED or f in B.FIXED_EVE or f in B.EMBED_EVE or f in B.TABLE_MODS)
    over_b = inplace and nb > n          # 원문 길이까지만(패딩 안 씀)
    if ov or not tok or over_b:
        ng += 1; print('NG', i, ov[:1], '' if tok else '토큰', '바이트 %d>%d' % (nb, n) if over_b else '', '|', t)
print('검사 %d줄 · 문제 %d' % (len(P), ng))

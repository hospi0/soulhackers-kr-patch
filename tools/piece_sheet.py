# -*- coding: utf-8 -*-
"""파일별 글 조각 표본을 글꼴로 그려 진짜 글인지 눈으로 판정 — python tools/piece_sheet.py 파일... → work/survey/pieces_<파일>.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import scan_text, ocrmap
G = ocrmap.glyphs()
for fn in sys.argv[1:]:
    d = open(os.path.join(ROOT, 'work', 'disc1', fn), 'rb').read()
    P = scan_text.pieces(d)
    step = max(1, len(P) // 30); pick = P[::step][:30]
    W = 120 + 17 * min(40, max(len(c) for _, c in pick)); im = Image.new('L', (W, 18 * len(pick) + 4), 0); dr = ImageDraw.Draw(im)
    for r, (st, c) in enumerate(pick):
        dr.text((2, r * 18 + 3), '%06X' % st, fill=120)
        for k, g in enumerate(c[:40]):
            im.paste(Image.fromarray((G[g] * 255).astype(np.uint8)), (60 + k * 17, r * 18 + 1))
    im.save(os.path.join(ROOT, 'work', 'survey', 'pieces_%s.png' % fn))

# -*- coding: utf-8 -*-
r"""받은 스테이트 21장의 VDP1 스프라이트 → 디스크 파일(압축 없이) 위치 짝짓기 + 실제 색 그림판 (2026-11-23)
  스테이트는 work/mem/s<N>/ (tools/state.py). 파일은 DAT·SND 뺀 119개.
  출력: work/states_map.tsv(스테이트·VRAM·크기·pm·colr·자리·파일:위치) · work/check/스테이트별_스프라이트/s<N>.png
  python tools/state_sprites.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import vdp1cmd, vdp2render as V, spritesheet as SS
from iso import Disc


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    D = Disc(1); files = {p.strip('/'): D.read(p.strip('/')) for p, l, s in D.files if not p.endswith(('.DAT', '.SND'))}
    out = os.path.join(ROOT, 'work', 'check', '스테이트별_스프라이트'); os.makedirs(out, exist_ok=True)
    rows = []
    for k in range(1, 25):   # s22 = 결과 화면(継続中), s23 = 랭킹, s24 = 결과(結果) — 2026-11-23
        s = 's%d' % k
        if not os.path.isdir(os.path.join(ROOT, 'work', 'mem', s)): continue
        v = vdp1cmd.load(os.path.join(ROOT, 'work', 'mem', s)); _, _, cram = V.load(s)
        items = []; seen = set()
        for i, cmd, pm, col, sa, w, h, x, y in vdp1cmd.cmds(v):
            if (sa, w, h, col) in seen or w < 8 or h < 8: continue
            seen.add((sa, w, h, col)); mode = (pm >> 3) & 7
            nb = w * h // 2 if mode in (0, 1) else w * h if mode in (2, 3, 4) else w * h * 2
            data = bytes(v[sa:sa + nb]); hit = ''
            if data.strip(b'\0'):
                for fn, fd in files.items():
                    j = fd.find(data)
                    if j >= 0: hit = '%s:%X' % (fn, j); break
            rows.append((s, '%05X' % sa, w, h, '%04X' % pm, '%04X' % col, x, y, hit))
            im = SS.sprite(v, cram, pm, col, sa, w, h)
            if im is not None: items.append(('%05X %s' % (sa, hit or '?'), im))
        W = 1400; xx = yy = rh = 0; S = Image.new('RGB', (W, 4000), (50, 50, 50)); Dd = ImageDraw.Draw(S)
        for lab, im in items:
            im = Image.fromarray(im.astype(np.uint8))
            if xx + max(im.width, 120) > W: xx = 0; yy += rh + 14; rh = 0
            Dd.text((xx, yy), lab, fill=(255, 255, 0)); S.paste(im, (xx, yy + 12)); xx += max(im.width, 120) + 6; rh = max(rh, im.height)
        S.crop((0, 0, W, yy + rh + 14)).save(os.path.join(out, '%s.png' % s))
    with open(os.path.join(ROOT, 'work', 'states_map.tsv'), 'w', encoding='utf-8') as f:
        f.write('state\tvram\tw\th\tpm\tcolr\tx\ty\tsrc\n')
        for r in rows: f.write('\t'.join(map(str, r)) + '\n')
    print(len(rows), '스프라이트,', sum(1 for r in rows if r[-1]), '개 파일과 짝지음')


if __name__ == '__main__':
    main()

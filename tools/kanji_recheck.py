# -*- coding: utf-8 -*-
r"""한자 전수 재판독(2026-11-25, 하스피 «한자 점검해») — 글에 쓰이는 한자 칸(0x258~)을 «낱자 하나씩» 크게(6배) 떼어 그려
  Windows 일본어 OCR 로 다시 읽고(문맥 없이 모양만), 판독표(data/charmap.tsv)와 다른 칸을 시트로 → 눈 확인
  python tools/kanji_recheck.py render  → work/ocr2/img_*.png + slots.json
  powershell -ExecutionPolicy Bypass -File tools\winocr.ps1 -Dir work\ocr2
  python tools/kanji_recheck.py diff    → work/ocr2/diff.tsv + work/ocr2/diff_NN.png"""
import collections, glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import ocrmap, charmap, extract_all
OUT = os.path.join(ROOT, 'work', 'ocr2'); K0 = 0x258; Z = 6; PITCH = 16 * Z + 60; PER = 12; ROWS = 20


def used():
    c = collections.Counter()
    for f in glob.glob(os.path.join(ROOT, 'work', 'disc1', '*')):
        b = os.path.basename(f)
        if b in extract_all.SKIP or f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        for st, en, toks in extract_all.messages(open(f, 'rb').read()):
            c.update(v for k, v in toks if k == 't' and v >= K0)
    return c


def render():
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, 'img_*')): os.remove(f)
    g = ocrmap.glyphs(); ks = sorted(k for k in used() if g[k].any())
    slots = {}; per_img = PER * ROWS
    for p in range(0, len(ks), per_img):
        part = ks[p:p + per_img]; im = Image.new('L', (40 + PITCH * PER, 40 + (16 * Z + 50) * ROWS), 255)
        for i, k in enumerate(part):
            x = 20 + (i % PER) * PITCH; y = 20 + (i // PER) * (16 * Z + 50)
            im.paste(Image.fromarray(((1 - g[k]) * 255).astype(np.uint8)).resize((16 * Z, 16 * Z), Image.NEAREST), (x, y))
        name = 'img_%03d' % (p // per_img); im.save(os.path.join(OUT, name + '.png')); slots[name] = part
    json.dump(slots, open(os.path.join(OUT, 'slots.json'), 'w')); print('한자 칸', len(ks), '그림', len(slots))


def diff():
    slots = json.load(open(os.path.join(OUT, 'slots.json'))); m = charmap.load(); cnt = used(); got = {}
    for name, part in slots.items():
        p = os.path.join(OUT, name + '.txt')
        if not os.path.exists(p): continue
        for ln in open(p, encoding='utf-8'):
            f = ln.rstrip('\n').split('\t')
            if len(f) < 5: continue
            w, x, y, ww, hh = f[0], *map(float, f[1:])
            for j, ch in enumerate(w):
                cx = x + ww * (j + 0.5) / len(w); cy = y + hh / 2
                col = int((cx - 20) // PITCH); row = int((cy - 20) // (16 * Z + 50)); i = row * PER + col
                if 0 <= col < PER and 0 <= i < len(part): got.setdefault(part[i], ch)
    rows = []
    for name, part in slots.items():
        for k in part:
            cur = m.get(k, ('', ''))[0]; o = got.get(k, '')
            if o and o != cur: rows.append((k, cur, o, m.get(k, ('', ''))[1], cnt[k]))
    with open(os.path.join(OUT, 'diff.tsv'), 'w', encoding='utf-8') as f:
        f.write('칸\t현재\t낱자OCR\t근거\t사용\n')
        for r in rows: f.write('%03X\t%s\t%s\t%s\t%d\n' % r)
    g = ocrmap.glyphs(); FJ = ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 30); FS = ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 13)
    for p in range(0, len(rows), 60):
        part = rows[p:p + 60]; S = Image.new('RGB', (6 * 250, 10 * 80 + 10), (250, 250, 250)); D = ImageDraw.Draw(S)
        for i, (k, cur, o, why, n) in enumerate(part):
            x = (i % 6) * 250 + 5; y = (i // 6) * 80 + 5
            S.paste(Image.fromarray(((1 - g[k]) * 255).astype(np.uint8)).resize((64, 64), Image.NEAREST), (x, y))
            D.text((x + 72, y), cur, font=FJ, fill=(200, 0, 0)); D.text((x + 120, y), o, font=FJ, fill=(0, 120, 0))
            D.text((x + 72, y + 44), '%03X %s %d회' % (k, why[:8], n), font=FS, fill=(80, 80, 80))
        S.save(os.path.join(OUT, 'diff_%02d.png' % (p // 60)))
    print('낱자 OCR 읽힌 칸 %d · 판독표와 다름 %d · 시트 %d장' % (len(got), len(rows), (len(rows) + 59) // 60))


if __name__ == '__main__':
    {'render': render, 'diff': diff}[sys.argv[1]]()

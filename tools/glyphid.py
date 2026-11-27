# -*- coding: utf-8 -*-
r"""한자 칸(0x258~0x7FF) 판독 (2026-11-24, darksavior glyphid.py 에서) — 실제 글 줄을 크게 그려 Windows 일본어 OCR 로 읽고 칸마다 다수결
  가나·ASCII = 고정 표(ocrmap.fixed)로 일본어 폰트 글자, 한자 칸·기호 칸 = 게임 글리프 4배. 칸 간격 고정 → OCR 글자 x 중심으로 칸 짚기.
  글 = EVENT.BIN · TALK*.EVE · I_SHOP*.EVE · GOMADEN.EVE · A_01.BIN 의 2바이트 코드 줄(0xFF xx 에서 끊음)
  python tools/glyphid.py render  → work/ocr/img_*.png + slots.json
  powershell -ExecutionPolicy Bypass -File tools\winocr.ps1 -Dir work\ocr
  python tools/glyphid.py vote    → work/ocr/vote.tsv (칸 16진 · 1위 · 득표 · 총표 · 2·3위)"""
import collections, glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import ocrmap
OUT = os.path.join(ROOT, 'work', 'ocr')
JFONT = r'C:\Windows\Fonts\BIZ-UDGothicB.ttc'
SC = 4; PITCH = 72; H = 84; PER_IMG = 50; K0 = 0x258
FILES = ['EVENT.BIN', 'GOMADEN.EVE', 'A_01.BIN'] + [os.path.basename(f) for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc1', 'TALK*.EVE')) + glob.glob(os.path.join(ROOT, 'work', 'disc1', 'I_SHOP*.EVE')))]


def runs(d):
    out = []; cur = []; i = 0
    while i < len(d) - 1:
        b = d[i]
        if 0xC0 <= b < 0xE0 and 0x80 <= d[i + 1] < 0xC0:
            cur.append(((b & 0x1F) << 6) | (d[i + 1] & 0x3F)); i += 2; continue
        if len(cur) >= 2: out.append(cur)
        cur = []; i += 2 if b == 0xFF else 1
    if len(cur) >= 2: out.append(cur)
    return out


def corpus():
    L = []
    for f in FILES: L += runs(open(os.path.join(ROOT, 'work', 'disc1', f), 'rb').read())
    return L


def render():
    FX = ocrmap.fixed(); G = ocrmap.glyphs(); os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, 'img_*')): os.remove(f)
    font = ImageFont.truetype(JFONT, 48)
    seen = set(); uniq = []
    for ln in corpus():
        if len(ln) > 30 or not any(c >= K0 for c in ln): continue
        k = tuple(ln)
        if k not in seen: seen.add(k); uniq.append(ln)
    slots = {}
    for i in range(0, len(uniq), PER_IMG):
        chunk = uniq[i:i + PER_IMG]; wmax = max(len(x) for x in chunk)
        im = Image.new('L', (40 + PITCH * wmax, 20 + H * len(chunk)), 255); dr = ImageDraw.Draw(im)
        name = 'img_%04d' % (i // PER_IMG); sl = []
        for r, ln in enumerate(chunk):
            y = 10 + r * H; row = []
            for k, c in enumerate(ln):
                x0 = 20 + k * PITCH
                if c in FX and c < K0:
                    ch = FX[c]; ch = chr(ord(ch) + 0xFEE0) if ch < '\x7f' else ch
                    dr.text((x0 + 6, y + 10), ch, font=font, fill=0); row.append(None)
                else:
                    big = Image.fromarray(((1 - G[c]) * 255).astype(np.uint8)).resize((16 * SC, 16 * SC), Image.NEAREST)
                    im.paste(big, (x0 + 4, y + 6)); row.append(c)
            sl.append(row)
        im.save(os.path.join(OUT, name + '.png')); slots[name] = sl
    json.dump(slots, open(os.path.join(OUT, 'slots.json'), 'w'))
    print('줄', len(uniq), '그림', len(slots))


def vote():
    slots = json.load(open(os.path.join(OUT, 'slots.json')))
    V = collections.defaultdict(collections.Counter)
    for name, sl in slots.items():
        p = os.path.join(OUT, name + '.txt')
        if not os.path.exists(p): continue
        for ln in open(p, encoding='utf-8'):
            f = ln.rstrip('\n').split('\t')
            if len(f) < 5: continue
            word, x, y, w, h = f[0], *map(float, f[1:])
            r = int((y + h / 2 - 10) // H)
            if not (0 <= r < len(sl)): continue
            n = len(word)
            for j, ch in enumerate(word):
                k = int((x + w * (j + 0.5) / n - 20) // PITCH)
                if 0 <= k < len(sl[r]) and sl[r][k] is not None:
                    V[sl[r][k]][ch] += 1
    with open(os.path.join(OUT, 'vote.tsv'), 'w', encoding='utf-8') as o:
        o.write('칸\t1위\t득표\t총표\t그다음\n')
        for g in sorted(V):
            c = V[g]; top = c.most_common(3)
            o.write('%03X\t%s\t%d\t%d\t%s\n' % (g, top[0][0], top[0][1], sum(c.values()), ' '.join('%s%d' % t for t in top[1:])))
    print('표 받은 칸', len(V))


if __name__ == '__main__':
    {'render': render, 'vote': vote}[sys.argv[1]]()

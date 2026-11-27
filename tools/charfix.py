# -*- coding: utf-8 -*-
r"""판독표 교정 후보 시트(2026-11-25) — 한자 칸(0x258~) 중 «근거 약함(OCR약·모양)» 이거나
  «OCR 글자가 모양 대조 순위 6위 밖»(OCR 이 문맥으로 엉뚱하게 읽은 것: 令→下, 格→枯 등)인 칸을 뽑아
  글리프 4배 + 현재 판독 + 모양 후보 5 + 쓰인 문맥 2개를 한 장에 → work/charfix/sheet_NN.png · 목록 work/charfix/cand.tsv
  교정은 tools/charmap.py MANUAL 에 적고 python tools/charmap.py → python tools/extract_all.py
  python tools/charfix.py"""
import collections, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import ocrmap, charmap, extract_all
OUT = os.path.join(ROOT, 'work', 'charfix'); K0 = 0x258


def kanji_cands():
    out = []
    for hi in list(range(0x88, 0xA0)) + list(range(0xE0, 0xEB)):
        for lo in range(0x40, 0xFD):
            if lo == 0x7F: continue
            try: out.append(bytes([hi, lo]).decode('cp932'))
            except UnicodeDecodeError: pass
    return out + list('々〆〇ー－―‐・…‥')


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(OUT, exist_ok=True)
    m = charmap.load(); raw = ocrmap.glyphs()
    use = collections.Counter(); ctx = collections.defaultdict(list)
    import glob
    for f in glob.glob(os.path.join(ROOT, 'work', 'disc1', '*')):
        b = os.path.basename(f)
        if b in extract_all.SKIP or f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        for st, en, toks in extract_all.messages(open(f, 'rb').read()):
            codes = [v for k, v in toks if k == 't']; use.update(codes)
            for i, c in enumerate(codes):
                if c >= K0 and len(ctx[c]) < 2:
                    ctx[c].append(''.join(m.get(x, ('?', ''))[0] for x in codes[max(0, i - 3):i + 4]))
    ks = [k for k in sorted(use) if k >= K0 and raw[k].any()]
    chars = kanji_cands()
    G, GA = zip(*[ocrmap.norm(raw[k]) for k in ks]); G = np.stack(G); GA = np.array(GA); S = None
    for path in (r'C:\Windows\Fonts\msgothic.ttc', r'C:\Windows\Fonts\meiryo.ttc', r'C:\Windows\Fonts\YuGothM.ttc'):
        F = ImageFont.truetype(path, 32); R = []; RA = []
        for ch in chars:
            im = Image.new('L', (44, 44)); ImageDraw.Draw(im).text((4, 2), ch, font=F, fill=255)
            v, ar = ocrmap.norm(np.array(im) / 255.0); R.append(v); RA.append(ar)
        s1 = G @ np.stack(R).T - 0.3 * np.abs(np.log(GA[:, None] / np.array(RA)[None, :]))
        S = s1 if S is None else np.maximum(S, s1)
    idx = {c: i for i, c in enumerate(chars)}; cand = []
    for r, k in enumerate(ks):
        ch, why = m.get(k, ('', ''))
        order = np.argsort(-S[r]); top = [chars[j] for j in order[:5]]
        rank = int(np.nonzero(order == idx[ch])[0][0]) if ch in idx else 9999
        weak = not why.startswith(('OCR', '고정', '손')) or why.startswith('OCR약')
        if weak or rank >= 6: cand.append((k, ch, why, rank, top, use[k], ctx[k]))
    with open(os.path.join(OUT, 'cand.tsv'), 'w', encoding='utf-8') as f:
        f.write('칸\t현재\t근거\t모양순위\t모양후보\t사용\t문맥\n')
        for k, ch, why, rank, top, n, cx in cand: f.write('%03X\t%s\t%s\t%d\t%s\t%d\t%s\n' % (k, ch, why, rank, ''.join(top), n, ' / '.join(cx)))
    FJ = ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 22); FS = ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 14)
    per = 30
    for p in range(0, len(cand), per):
        part = cand[p:p + per]; S2 = Image.new('RGB', (1500, 70 * len(part) + 10), (250, 250, 250)); D = ImageDraw.Draw(S2)
        for i, (k, ch, why, rank, top, n, cx) in enumerate(part):
            y = 5 + i * 70
            g = Image.fromarray(((1 - raw[k]) * 255).astype(np.uint8)).resize((64, 64), Image.NEAREST); S2.paste(g, (5, y))
            D.text((80, y + 2), '%03X' % k, font=FS, fill=(0, 0, 160)); D.text((80, y + 22), '현재 ' if False else '', font=FS, fill=0)
            D.text((130, y + 10), ch, font=ImageFont.truetype(r'C:\Windows\Fonts\YuGothM.ttc', 40), fill=(200, 0, 0))
            D.text((190, y + 4), '모양: ' + ' '.join(top), font=FJ, fill=(0, 100, 0))
            D.text((190, y + 36), '%s · 순위 %s · %d회 · %s' % (why, rank if rank < 9999 else '-', n, '  /  '.join(cx)), font=FS, fill=(60, 60, 60))
        S2.save(os.path.join(OUT, 'sheet_%02d.png' % (p // per)))
    print('후보 %d칸 · 시트 %d장' % (len(cand), (len(cand) + per - 1) // per))


if __name__ == '__main__':
    main()

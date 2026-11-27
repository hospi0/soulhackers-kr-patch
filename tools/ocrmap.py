# -*- coding: utf-8 -*-
r"""글꼴 칸 → 문자 표 (2026-11-24, cyberdoll ocrmap.py 에서) — A_FONT16.BIN 16×16 1bpp 2,048칸을
  MS 고딕·메이리오·유고딕으로 그린 JIS 전각 문자와 모양 대조(글자 상자로 잘라 14×14 흐린 벡터, 내적 − 가로세로 비 감점)
  고정 칸: ASCII = 0x140+(c−0x20) / 히라가나 0x1A1~ / 가타카나 0x201~ (JIS 순서) — 이 칸들은 대조 대신 표로 박음(대조는 검산용으로 같이 적음)
  → work/charmap.tsv (칸 16진 · 문자 · 점수 · 2등 · 2등 점수) · python tools/ocrmap.py"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
H = 'ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん'
K = 'ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ'


def glyphs():
    d = open(os.path.join(ROOT, 'work', 'disc1', 'A_FONT16.BIN'), 'rb').read()
    g = np.zeros((2048, 16, 16), np.uint8)
    for c in range(2048):
        for y in range(16):
            w = d[c * 32 + y * 2] << 8 | d[c * 32 + y * 2 + 1]
            for x in range(16): g[c, y, x] = w >> (15 - x) & 1
    return g


def candidates():
    chars = []
    for hi in list(range(0x81, 0x85)) + list(range(0x88, 0xA0)) + list(range(0xE0, 0xEB)):
        for lo in range(0x40, 0xFD):
            if lo == 0x7F: continue
            try: chars.append(bytes([hi, lo]).decode('cp932'))
            except UnicodeDecodeError: pass
    return chars


def norm(img, size=14):
    ys, xs = np.nonzero(img)
    if len(ys) == 0: return np.zeros(size * size, np.float32), 1.0
    crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32) * 255
    h, w = crop.shape
    v = np.asarray(Image.fromarray(crop.astype(np.uint8)).resize((size, size), Image.BILINEAR), np.float32).reshape(-1)
    v -= v.mean(); v /= (np.linalg.norm(v) + 1e-6)
    return v, (w + 1) / (h + 1)


def fixed():
    m = {}
    for c in range(0x21, 0x7F): m[0x120 + c] = chr(c)
    for i, ch in enumerate(H): m[0x1A1 + i] = ch
    for i, ch in enumerate(K): m[0x201 + i] = ch
    return m


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    raw = glyphs(); n = 2048
    G, GA = zip(*[norm(raw[i]) for i in range(n)]); G = np.stack(G); GA = np.array(GA)
    chars = candidates() + [chr(c) for c in range(0x21, 0x7F)]
    S = None
    for path in (r'C:\Windows\Fonts\msgothic.ttc', r'C:\Windows\Fonts\meiryo.ttc', r'C:\Windows\Fonts\YuGothM.ttc'):
        F = ImageFont.truetype(path, 32); R = []; RA = []
        for ch in chars:
            im = Image.new('L', (44, 44)); ImageDraw.Draw(im).text((4, 2), ch, font=F, fill=255)
            v, ar = norm(np.array(im) / 255.0); R.append(v); RA.append(ar)
        R = np.stack(R); RA = np.array(RA)
        s1 = G @ R.T - 0.3 * np.abs(np.log(GA[:, None] / RA[None, :]))
        S = s1 if S is None else np.maximum(S, s1)
    order = np.argsort(-S, axis=1)[:, :2]; FX = fixed(); bad = 0
    with open(os.path.join(ROOT, 'work', 'charmap.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('칸\t문자\t점수\t2등\t2등점수\n')
        for i in range(n):
            if not raw[i].any(): f.write('%03X\t\t0\t\t0\n' % i); continue
            a, b = order[i]
            if i in FX:
                if chars[a] not in (FX[i], chr(ord(FX[i]) + 0xFEE0) if FX[i] < '\x7f' else FX[i]): bad += 1
                f.write('%03X\t%s\t1.000\t%s\t%.3f\n' % (i, FX[i], chars[a], S[i, a])); continue
            f.write('%03X\t%s\t%.3f\t%s\t%.3f\n' % (i, chars[a], S[i, a], chars[b], S[i, b]))
    sc = [S[i, order[i][0]] for i in range(n) if raw[i].any() and i not in FX]
    print('대조 칸 %d · 점수 중간값 %.3f · 0.6 미만 %d · 고정 칸 중 대조와 다른 것 %d' % (len(sc), float(np.median(sc)), sum(1 for x in sc if x < 0.6), bad))


if __name__ == '__main__':
    main()

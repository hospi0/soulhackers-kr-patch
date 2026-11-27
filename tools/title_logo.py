# -*- coding: utf-8 -*-
r"""타이틀 로고 한글(2026-11-27): «데빌 서머너»(하스피 그림 my files/b2034…png — 회색 바둑판이 구워진 RGB → 빨강 성분으로 떼어냄) → 408×72,
  «소울 해커즈»(나눔고딕 ExtraBold, 원본 ソウルハッカーズ 글자 범위 y7~22·x8~223, 흰 몸통+어두운 테두리) → 232×32.
  색 = 원본 스프라이트가 쓴 색 번호만(타이틀 스테이트 CRAM, 128색 뱅크 0x80|p&0x7F).
  python tools/title_logo.py → work/title/타이틀로고_미리보기.png + devil_kr.npy·soul_kr.npy"""
import os, struct, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'work', 'mem', '타이틀')
V = open(os.path.join(D, 'VDP1_VRAM.bin'), 'rb').read(); C = open(os.path.join(D, 'CRAM.bin'), 'rb').read()
def cram(i):
    i = int(i); v = struct.unpack('<H', C[i * 2:i * 2 + 2])[0]; return [(v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3]
def sprite(a, w, h): return np.frombuffer(V[a:a + w * h], np.uint8).reshape(h, w).astype(int)
def quant(rgba, used):
    pal = np.array([cram(0x80 | (p & 0x7F)) for p in used], np.int64)
    rgb = rgba[..., :3].reshape(-1, 3).astype(np.int64); al = rgba[..., 3].reshape(-1)
    dd = ((rgb[:, None, :] - pal[None, :, :]) ** 2).sum(2); idx = np.array(used)[dd.argmin(1)]
    idx[al < 128] = 0
    return idx.reshape(rgba.shape[:2]).astype(np.uint8)
def show(px):
    h, w = px.shape; img = np.zeros((h, w, 4), np.uint8)
    for y, x in zip(*np.nonzero(px)): img[y, x, :3] = cram(0x80 | (int(px[y, x]) & 0x7F)); img[y, x, 3] = 255
    return Image.fromarray(img)
BANK = list(range(1, 126))   # 126(0xFE)·127(0xFF) 제외 — 스프라이트 형식 C 에서 0xFE = «그림자» 특수 코드(배경만 어둡게 → ㅂ 오른쪽 위 획 속 빔, 2026-11-27), 0xFF = 끝 코드                                                       # 타이틀 128색 뱅크 전부(두 스테이트 CRAM 같음 — 고정)
def solid(rgb, used, edge):
    """둘레를 반투명 섞임 없이: 알파 >= edge 만 칠하고 색은 used 안에서 가장 가까운 것"""
    a = np.asarray(rgb).astype(int); return quant(np.dstack([a[..., :3], np.where(a[..., 3] >= edge, 255, 0)]), used)
def devil():
    """얼룩 고침(2026-11-27 실기 «데빌서머너에 얼룩»): ① 가장자리 누런 띠 = 줄일 때 회색 바둑판이 섞인 색 → 알파 곱한 색만 줄이고 나눔(바둑판 0 기여)
    ② 획 안 보라 구멍 = 투명 화소 → 사방이 막힌 빈 곳 전부 메움 ③ 색은 노랑 빼고 빨강·주황만"""
    a = np.asarray(Image.open(os.path.join(ROOT, 'work', 'title', '데빌서머너_로고_하스피.png')).convert('RGB')).astype(float)
    sat = a.max(2) - a.min(2)
    m = Image.fromarray(((sat > 45) & (a[..., 0] > 60)).astype(np.uint8) * 255)
    m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    box = m.getbbox(); m = m.crop(box); a = a[box[1]:box[3], box[0]:box[2]]
    W, H = 404, 70; s = min(W / m.width, H / m.height); sz = (int(m.width * s), int(m.height * s))
    al = np.asarray(m).astype(float) / 255
    r = 1.2 / s
    g = lambda v: np.asarray(Image.fromarray(v.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)).resize(sz, Image.BOX)).astype(float)
    pre = [g(a[..., c] * al) for c in range(3)]
    A = g(al * 255) / 255
    rgb = np.dstack(pre) / np.maximum(A, 1e-3)[..., None]
    # 얼룩(2026-11-27 실기 «얼룩은 왜 못지우냐»): 원본 그림 질감의 진한 적갈색·주황 반점이 작은 해상도에선 얼룩 → 색을 크게 뭉개 «부드러운 빨강→주황 흐름»만 남김
    w = np.maximum(A, 1e-3)
    sm = [np.asarray(Image.fromarray((rgb[..., c] * A).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(float) for c in range(3)]
    sA = np.asarray(Image.fromarray((A * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(float) / 255
    rgb = np.dstack(sm) / np.maximum(sA, 1e-3)[..., None]
    global fill_holes
    def fill_holes(b):                                                           # 바깥에서 흘려 채워 안 닿는 빈 곳 = 구멍
        free = ~np.pad(b, 1); out = np.zeros_like(free); out[0, :] = out[-1, :] = out[:, 0] = out[:, -1] = True; out &= free
        while True:
            nxt = out.copy(); nxt[1:] |= out[:-1]; nxt[:-1] |= out[1:]; nxt[:, 1:] |= out[:, :-1]; nxt[:, :-1] |= out[:, 1:]; nxt &= free
            if (nxt == out).all(): break
            out = nxt
        return ~out[1:-1, 1:-1]
    on0 = A >= 0.45; hole = fill_holes(on0) & ~on0; on = on0.copy()          # 작은 구멍(≤12화소)만 메움 — ㅁ·ㅂ 속 같은 진짜 빈 곳은 그대로
    seen = np.zeros_like(hole)
    for y, x in zip(*np.nonzero(hole)):
        if seen[y, x]: continue
        st = [(y, x)]; comp = []; seen[y, x] = True
        while st:
            cy, cx = st.pop(); comp.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < hole.shape[0] and 0 <= nx < hole.shape[1] and hole[ny, nx] and not seen[ny, nx]: seen[ny, nx] = True; st.append((ny, nx))
        if len(comp) <= 12:
            for cy, cx in comp: on[cy, cx] = True
    hole = on & (A < 0.45)
    for _ in range(20):                                                          # 메운 자리 색 = 이웃 색 번져 채움
        if not hole.any(): break
        known = ~hole; acc = np.zeros_like(rgb); n = np.zeros(hole.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(np.roll(known, dy, 0), dx, 1); acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * k[..., None]; n += k
        f = hole & (n > 0); rgb[f] = acc[f] / n[f][:, None]; hole &= ~f
    can = np.zeros((72, 408, 4)); y0, x0 = (72 - sz[1]) // 2, (408 - sz[0]) // 2
    can[y0:y0 + sz[1], x0:x0 + sz[0], :3] = rgb; can[y0:y0 + sz[1], x0:x0 + sz[0], 3] = on * 255
    reds = [p for p in BANK if (lambda c: c[0] >= 150 and c[1] <= 110 and c[2] <= 40)(cram(0x80 | p))]
    px = quant(can.clip(0, 255).astype(int), reds)
    on = px > 0; ring = np.zeros_like(on)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): ring |= np.roll(np.roll(on, dy, 0), dx, 1)
    px[ring & ~on] = 1
    # 테두리만으로 막힌 빈 곳(ㅂ 오른쪽 위 — 획 끝 둘이 닿을락 말락해 검은 테두리가 이어져 «속 빈 획»처럼 보임, 2026-11-27 실기) → 이웃 빨강으로 채움
    #  획 자체가 둘러싼 진짜 빈 곳(ㅂ 가운데·ㅁ 속)은 그대로
    shell = px > 0; real = fill_holes(on) & ~on
    fake = fill_holes(shell) & ~shell & ~real
    grow = fake.copy()                                                           # 빈 곳 + 그 둘레 테두리 화소까지 채울 자리
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)): grow |= np.roll(np.roll(fake, dy, 0), dx, 1) & (px == 1)
    px[grow] = 0
    for _ in range(100):
        left = grow & (px == 0)
        if not left.any(): break
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = np.roll(np.roll(px, dy, 0), dx, 1); f = left & (px == 0) & (nb > 1); px[f] = nb[f]
    hole = fill_holes(px > 1) & ~(px > 1); seen = np.zeros_like(hole)          # 남은 작은 구멍(≤12화소, 검은 점으로 보임)도 채움
    for y, x in zip(*np.nonzero(hole)):
        if seen[y, x]: continue
        st = [(y, x)]; comp = []; seen[y, x] = True
        while st:
            cy, cx = st.pop(); comp.append((cy, cx))
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < 72 and 0 <= nx < 408 and hole[ny, nx] and not seen[ny, nx]: seen[ny, nx] = True; st.append((ny, nx))
        if len(comp) <= 12:
            for cy, cx in comp: px[cy, cx] = 0
            for _ in range(6):
                for cy, cx in comp:
                    if px[cy, cx] > 1: continue
                    nb = [px[cy + dy, cx + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if px[cy + dy, cx + dx] > 1]
                    if nb: px[cy, cx] = nb[0]
    on = px > 1; ring = np.zeros_like(on)                                        # 채운 뒤 테두리 다시
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): ring |= np.roll(np.roll(on, dy, 0), dx, 1)
    px[(px == 1)] = 0; px[ring & ~on] = 1
    FILL_B_TOP = False                                                            # ㅂ 위 틈 채우기 — 채우면 «밀»로 읽힘(안: work/title/데빌서머너_ㅂ위채움_안.png)
    return sprite(0x1c800, 408, 72), px
def soul_mask(font):
    """«소울 해커즈» 한 번에 렌더 → (몸통 알파, 테두리 마스크) 232×32, 높이 26·가로 1.3배·왼쪽 x6 — 네 장 모두 같은 크기"""
    F = ImageFont.truetype('C:/claude/utils/font/nanum-gothic/%s.ttf' % font, 8 * 22)
    t = '소울 해커즈'; bb = ImageDraw.Draw(Image.new('L', (8, 8))).textbbox((0, 0), t, font=F)
    big = Image.new('L', (bb[2] - bb[0] + 64, bb[3] - bb[1] + 64), 0); ImageDraw.Draw(big).text((32 - bb[0], 32 - bb[1]), t, font=F, fill=255)
    ol = big.filter(ImageFilter.MaxFilter(25)); box = ol.getbbox(); big = big.crop(box); ol = ol.crop(box)
    k = min(220 / (big.width * 1.3), 26 / big.height); sz = (int(big.width * k * 1.3), int(big.height * k))
    x0, y0 = 6, (32 - sz[1]) // 2
    m = np.zeros((32, 232)); e = np.zeros((32, 232))
    m[y0:y0 + sz[1], x0:x0 + sz[0]] = np.asarray(big.resize(sz, Image.LANCZOS)) / 255
    e[y0:y0 + sz[1], x0:x0 + sz[0]] = np.asarray(ol.resize(sz, Image.LANCZOS)) / 255
    return m, e
def soul():
    """원본은 232×32 «네 장»(A_TITLE 0x060347B0: 판 0x267000 + (j&1)*0xE8 + (j>>1)*0x5000) — 0 굵은 흰 글씨 · 1 흰 상자에 굵은 검은 글씨 · 2 가는 흰 글씨 · 3 흰 상자에 가는 검은 글씨.
    0장만 바꿨더니 깜빡이는 나머지 장이 원문(2026-11-27 실기 «선» 화면)"""
    greys = [p for p in BANK if (lambda c: max(c) - min(c) <= 40)(cram(0x80 | p))]
    W, D = np.array([248, 248, 248]), np.array([40, 40, 64]); K = np.array([8, 8, 8])
    out = []
    for j, font in enumerate(('NanumGothicExtraBold', 'NanumGothicExtraBold', 'NanumGothic', 'NanumGothic')):
        m, e = soul_mask(font)
        if j in (0, 2):                                                          # 흰 글씨 + 어두운 테두리
            rgb = W * m[..., None] + D * (1 - m[..., None]); al = (e >= 0.4) | (m >= 0.4)
        else:                                                                    # 흰 상자(잉크 범위 ±2) 안 검은 글씨
            ys, xs = np.nonzero(e >= 0.4); al = np.zeros((32, 232), bool)
            al[max(0, ys.min() - 2):min(32, ys.max() + 3), max(0, xs.min() - 3):min(232, xs.max() + 4)] = True
            rgb = K * m[..., None] + W * (1 - m[..., None])
        out.append(quant(np.dstack([rgb, np.where(al, 255, 0)]).astype(int), greys + [1]))
    return np.load(os.path.join(ROOT, 'work', 'title', 'soul_orig4.npy')) if os.path.exists(os.path.join(ROOT, 'work', 'title', 'soul_orig4.npy')) else None, np.array(out)
if __name__ == '__main__':
    o1, d = devil(); o2, s = soul()
    np.save(os.path.join(ROOT, 'work', 'title', 'devil_kr.npy'), d); np.save(os.path.join(ROOT, 'work', 'title', 'soul_kr.npy'), s)
    def pair(a, b):
        A, B = show(a), show(b); im = Image.new('RGBA', (A.width * 2 + 8, A.height), (40, 40, 60, 255)); im.paste(A, (0, 0), A); im.paste(B, (A.width + 8, 0), B)
        return im.resize((im.width * 3, im.height * 3), Image.NEAREST)
    ps = [pair(o1, d)] + [pair(o2[k], s[k]) for k in range(4)]
    out = Image.new('RGBA', (max(p.width for p in ps), sum(p.height + 12 for p in ps)), (40, 40, 60, 255)); y = 0
    for p_ in ps: out.paste(p_, (0, y)); y += p_.height + 12
    out.save(os.path.join(ROOT, 'work', 'title', '타이틀로고_미리보기.png')); print('ok')


LOGOS = ((0x1BC00, 408, 72, 'devil_kr.npy'), (0x27000, 232, 32, 'soul_kr.npy'))   # A_TITSPR.BIN(RAM 0x240000) 안 640폭 판 — A_TITLE 0x0603476E 가 0x25BC00·0x267000 에서 읽음


def patch(b):
    """A_TITSPR.BIN 바이트 → 로고 두 개를 한글로(색 번호 = VRAM 과 같은 번호)"""
    b = bytearray(b)
    for base, w, h, fn in LOGOS:
        px = np.load(os.path.join(ROOT, 'work', 'title', fn))
        frames = [(base, px)] if px.ndim == 2 else [(base + (k & 1) * 0xE8 + (k >> 1) * 0x5000, px[k]) for k in range(4)]   # 소울 해커즈 네 장
        for at, f in frames:
            assert f.shape == (h, w)
            for y in range(h): b[at + y * 640:at + y * 640 + w] = f[y].astype(np.uint8).tobytes()
    return bytes(b)

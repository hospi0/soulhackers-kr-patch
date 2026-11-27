# -*- coding: utf-8 -*-
r"""오프닝 그림 글자 한글화(2026-11-27, 하스피 «오프닝 그림글자 한글화해줘»)
  MESS.BIN(=EVE_MES.BIN 사본) 안 압축 없는 320×224 RGB555(빅엔디언, MSB 켬) 그림, 장당 0x23000.
  오프닝 = BASE + k×0x23000:  k0 글자 없는 섬 배경 · k2~k5 «五年前…» 네 줄이 한 줄씩 · k6~k8 «ネットワークという» 세 줄.
  장마다: 원본 글자 줄 상자 안을 k0 배경으로 되돌리고 → 한글(나눔고딕, 원본처럼 살짝 기울임, 흰 글씨+어두운 번짐 그림자)을 원본 줄 자리에.
  python tools/opening_kr.py            → 미리보기 work/opening/오프닝_미리보기.png (원본|한글)
  build 에서: patch(mess_bytes) → 고친 MESS.BIN 바이트"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASE, FR = 0x2E38800, 0x23000
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
S = 4                                   # 4배로 그려 줄임
SHEAR = 0.18                            # 원본 기울기
H = 16                                  # 글자 높이(원본 몸통 16px)
# 줄: (원본 줄 상자 y0, y1, 시작 x) — 원본 실측(k0 과 차이)
LINES_A = [(37, 63, 29), (76, 100, 29), (116, 138, 29), (154, 177, 29)]
LINES_B = [(37, 61, 29), (72, 97, 29), (141, 165, 29)]
TEXT_A = ['5년 전, 정부가 제창한', '「차기 정보 도시 정책」은', '그때까지 한낱 지방 도시에 불과했던', '이 거리의 모습을 크게 바꾸어 놓았다']
TEXT_B = ['네트워크라는', '전자의 그물에 감싸인 거리', '정보 환경 모델 도시 아마미의 탄생이다']
FRAMES = {2: (LINES_A, TEXT_A, 1), 3: (LINES_A, TEXT_A, 2), 4: (LINES_A, TEXT_A, 3), 5: (LINES_A, TEXT_A, 4),
          6: (LINES_B, TEXT_B, 1), 7: (LINES_B, TEXT_B, 2), 8: (LINES_B, TEXT_B, 3),
          26: (LINES_B + [(132, 140, 29)], TEXT_B + [''], 4)}       # k26 = 셋째 줄 «あまみ» 후리가나 붙은 장(실기에서 셋째 줄 나올 때 이 장 — 2026-11-27 «세번째줄 나올때 전부 일본어»)


def to_rgb(b):
    a = np.frombuffer(b, '>u2').reshape(224, 320).astype(np.int32)
    return np.dstack([(a & 31) << 3, ((a >> 5) & 31) << 3, ((a >> 10) & 31) << 3]).astype(np.uint8)


def to_555(img):
    a = img.astype(np.int32) >> 3
    v = 0x8000 | (a[..., 2] << 10) | (a[..., 1] << 5) | a[..., 0]
    return v.astype('>u2').tobytes()


def line_layer(text, x, ytop):
    """4배 그림(RGBA 1280×896): 흰 글씨 + 어두운 번짐 그림자"""
    W, Hh = 320 * S, 224 * S
    F = ImageFont.truetype(FONT, int(H * S * 1.05))
    m = Image.new('L', (W, Hh), 0); d = ImageDraw.Draw(m)
    bb = d.textbbox((0, 0), '가', font=F)
    d.text((x * S, ytop * S - bb[1]), text, font=F, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, SHEAR, -SHEAR * ytop * S - SHEAR * H * S, 0, 1, 0), Image.BICUBIC)
    shadow = m.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(S * 1.3))
    return m, shadow


def compose(orig, bg, lines, texts, n):
    img = orig.copy()
    for (y0, y1, x) in lines[:n]:                                     # 원본 글자 줄 → 배경으로
        img[max(0, y0 - 2):y1 + 3, :] = bg[max(0, y0 - 2):y1 + 3, :]
    big = Image.fromarray(img).resize((320 * S, 224 * S), Image.BICUBIC)
    acc_m = Image.new('L', big.size, 0); acc_s = Image.new('L', big.size, 0)
    for (y0, y1, x), t in list(zip(lines, texts))[:n]:
        m, s = line_layer(t, x, y0 + 4)
        acc_m = Image.fromarray(np.maximum(np.asarray(acc_m), np.asarray(m)))
        acc_s = Image.fromarray(np.maximum(np.asarray(acc_s), np.asarray(s)))
    a = np.asarray(big).astype(np.float32)
    sa = np.asarray(acc_s).astype(np.float32)[..., None] / 255 * 0.95
    a = a * (1 - sa) + np.array([10, 10, 20]) * sa
    ma = np.asarray(acc_m).astype(np.float32)[..., None] / 255
    a = a * (1 - ma) + np.array([250, 250, 250]) * ma
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize((320, 224), Image.LANCZOS)
    res = np.asarray(out).copy()
    keep = np.ones((224, 320), bool)                                   # 줄 상자 밖은 원본 화소 그대로
    for (y0, y1, x) in lines[:n]: keep[max(0, y0 - 6):y1 + 7, :] = False
    res[keep] = orig[keep]
    return res


def patch(m):
    m = bytearray(m)
    bg = to_rgb(bytes(m[BASE:BASE + FR]))
    for k, (lines, texts, n) in FRAMES.items():
        o = BASE + k * FR
        m[o:o + FR] = to_555(compose(to_rgb(bytes(m[o:o + FR])), bg, lines, texts, n))
    return bytes(m)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, HERE); import iso
    m = iso.Disc(1).read('MESS.BIN'); p = patch(m)
    rows = []
    for k in FRAMES:
        o = BASE + k * FR
        rows.append(np.hstack([to_rgb(m[o:o + FR]), np.full((224, 4, 3), 255, np.uint8), to_rgb(p[o:o + FR])]))
    img = Image.fromarray(np.vstack(rows)); img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    out = os.path.join(ROOT, 'work', 'opening', '오프닝_미리보기.png'); img.save(out); print(out)

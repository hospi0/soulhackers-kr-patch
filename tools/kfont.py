# -*- coding: utf-8 -*-
r"""소울 해커즈 한글 글꼴(2026-11-25, 선검기협전 kfont.py 에서) — A_FONT16.BIN(16×16 1bpp, 32 B 칸, 2,048칸)
  글 코드(11비트) = 글꼴 칸 번호 그대로 → 한글 음절을 «가나·한자 칸»(0x1A1~0x7FF 중 부호 아닌 칸, 잉크 있는 칸만)에 배정해 그림만 바꾼다.
  부호 칸(、。【】ー・…「」○× 등, 원본에서 가나·한자 아닌 글자)·0x000~0x1A0(기호·ASCII)은 그대로 → 번역의 부호는 그 칸을 씀.
  음절→칸 배정은 data/kmap.json 에 고정(덧붙이기만 — 빌드마다 칸이 움직이지 않게).
  글꼴 = Galmuri14(bdf), 원본 잉크 범위 줄 1~14·칸 1~14 에 맞춤(TOP 3).
  python tools/kfont.py → work/check/한글글꼴_표.png"""
import json, os, struct, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from bdf import Font
import charmap
G14 = Font(r'C:/claude/utils/font/Galmuri-v2.40.3/Galmuri14.bdf')
TOP = 3
KMAP = os.path.join(ROOT, 'data', 'kmap.json')
FONT = os.path.join(ROOT, 'work', 'disc1', 'A_FONT16.BIN')


def is_kana_kanji(ch):
    if not ch: return False
    n = unicodedata.name(ch, '')
    return n.startswith(('HIRAGANA', 'KATAKANA', 'CJK UNIFIED')) and ch != 'ー'


ELLIPSIS = [None]
WAVE = [None]
WAVE_SRC = 0x52B                                                  # 원본 글꼴의 물결(～) 칸 — 한자 칸이라 한글로 덮임
HUDTMP = [None]


def rank(tag): return 2 if tag.startswith('고정') else 1 if tag.startswith('OCR') else 0


def tables():
    """(덮을 칸 목록, 부호 글자→칸) — 판독표 기준"""
    m = charmap.load(); slots = []; keep = {}
    import ocrmap; g = ocrmap.glyphs()
    import tr_fix
    for k in range(0, 0x800):
        ch = m.get(k, ('', ''))[0]
        if ch in tr_fix.KANJI_KEEP and ch not in keep: keep[ch] = k; continue      # 한자 퀴즈용 — 칸 남김(2026-11-26)
        if 0x1A1 <= k and is_kana_kanji(ch) and g[k].any() and not 0x1FA <= k <= 0x1FF: slots.append(k)
        # ⛔빈 칸은 안 씀(2026-11-25): 0x1FA~0x1FF = 성·이름 글자를 실행 중에 그리는 칸(세이브 RAM 에 c7ba…c7bf 로 저장),
        #   0x1F4·0x7A2~ 등 빈 칸도 글에서 {XXX} 로 불림(실행 중 그림) → 한글로 덮으면 이름·글자가 깨진다
        elif ch and (ch not in keep or rank(m[k][1]) > rank(m[keep[ch]][1])): keep[ch] = k        # 확정(고정) > OCR > 모양 짐작 — 」·D 오판(2026-11-26)
        # ↑ 부호·영숫자·공백 = 원래 칸(같은 글자 여러 칸이면 앞 칸, 단 «모양» 짐작 칸보다 OCR 확실 칸 — 」 0x49 오판으로 «X」» 가 «XI» 로 찍힘, 2026-11-26)
    keep.setdefault(' ', 0x140); keep.setdefault('　', 0x140)
    HUDTMP[0] = slots.pop()                                            # 전투 파티 칸 이름 훅 임시 칸(tools/hud_hook.py, 2026-11-27)
    keep['…'] = ELLIPSIS[0] = slots.pop()                            # «…» 전용 전각 칸(원래 0x0F 는 ≤0x13F 라 반각 8px 로 찍혀 점 1~2개만 보임, 2026-11-26) — 맨 끝 칸(한글은 앞에서부터 배정)
    keep['～'] = WAVE[0] = slots.pop()                               # «～» 전용 칸(2026-11-27 하스피 «이 특수문자 원문도 그래?»): 판독표 0x19E «~» 는 실은 ♀(장비 «여성 전용» 표시 {FF1C}~{FF16}),
    #   번역의 물결 «~» 945줄이 ♀ 로 찍혔다 → 번역 물결은 빌더가 «～» 로 바꾸고 이 칸에 원본 0x52B 물결 그림을 옮김
    return slots, keep


def load():
    return json.load(open(KMAP, encoding='utf-8')) if os.path.exists(KMAP) else {}


def assign(chars, save=True):
    """한글 음절 집합 → {글자: 칸}. 이미 배정된 건 안 움직임. 칸 부족이면 AssertionError"""
    m = load(); slots, _ = tables(); used = set(m.values()); free = [k for k in slots if k not in used]
    for ch in sorted(set(chars) - set(m)):
        assert free, ('글꼴 칸 부족 — 한글 음절 %d 개, 칸 %d' % (len(set(chars) | set(m)), len(slots)))
        m[ch] = free.pop(0)
    if save: json.dump(m, open(KMAP, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return m


def is_ko(ch): return '가' <= ch <= '힣' or 'ㄱ' <= ch <= 'ㅣ'          # 낱자모(ㄹ 등, 외계어 대사)도 칸 배정


def glyph16(ch):
    g = G14.g.get(ord(ch)); assert g, ('Galmuri14 에 없는 글자', ch)
    pts, _ = G14.draw(ch); rows = [0] * 16
    for x, y in pts:
        x += 1; y -= TOP
        assert 0 <= x < 16 and 0 <= y < 16, ('칸 밖', ch, x, y); rows[y] |= 0x8000 >> x
    return struct.pack('>16H', *rows)


def build_font(m):
    f = bytearray(open(FONT, 'rb').read())
    # «…» 전용 칸: 가운데 높이 고른 점 셋(16px 전각)
    tables(); rows = [0] * 16
    for y in (8, 9): rows[y] = sum(0xC000 >> x for x in (2, 7, 12))
    f[32 * ELLIPSIS[0]:32 * ELLIPSIS[0] + 32] = struct.pack('>16H', *rows)
    for ch, k in m.items(): f[32 * k:32 * k + 32] = glyph16(ch)
    src = open(FONT, 'rb').read(); f[32 * WAVE[0]:32 * WAVE[0] + 32] = src[32 * WAVE_SRC:32 * WAVE_SRC + 32]
    return bytes(f)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    from PIL import Image
    s, keep = tables(); print('덮을 칸 %d · 부호 글자 %d' % (len(s), len(keep)))
    m = assign('가나다라마바사아자차카타파하한글패치소울해커즈', save=False); f = build_font(m)
    im = Image.new('L', (16 * 24, 16), 0); px = im.load()
    for i, ch in enumerate(list(m)[:24]):
        k = m[ch]
        for y in range(16):
            w = f[32 * k + 2 * y] << 8 | f[32 * k + 2 * y + 1]
            for x in range(16):
                if w >> (15 - x) & 1: px[i * 16 + x, y] = 255
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    im.resize((im.width * 3, 48)).save(os.path.join(ROOT, 'work', 'check', '한글글꼴_표.png'))

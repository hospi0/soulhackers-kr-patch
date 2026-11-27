# -*- coding: utf-8 -*-
r"""이름 입력 화면 한글화(2026-11-26, 하스피 «순서대로 쭉» — 남은 일 «이름 입력 한글 음절판»)

구조(EVE_NAME.BIN, 적재 0x06030000 — 조사 docs/00_초기조사.md «이름 입력»):
  · 네 쪽(漢字·ひらがな·カタカナ·英数字) 모두 EVE_KAN.BIN(JIS X 0208 16×16 1bpp, 번호 = (구-1)*94+(점-1), RAM 0x240000)에서 바로 그림.
    한 화면 9줄 × 13칸(0칸 = 머리).  ← → END = 0x68 0x67 0x1F7.
  · 漢字 표 0x6D54: 13칸 × 271줄(머리 44 + 他 줄), 위치 0x06056CC2.
    상수: 0x106(맨 위 줄 최대 = 줄수-9) 풀 0x1B66·0x1BE6·0x1F2E·0x20F2 / 0x10F(줄수) 0x1F2A / 0xDD0((줄수+1)*13) 0x20EE
          첫 묶음 머리 0x11B(あ) 0x20F0 / 끝 묶음 머리 0xC3B(他) 0x1F2C (0x85E·0xAF6·0xDCE 의 0xC3B = 他 머리 숨김 — 그대로)
  · ひらがな 0x88DA · カタカナ 0x89C4 값 표(EVE_KAN 번호, 9×13), 같은 자리 대사 코드 표(코드네임용) 0x6A56·0x6B56 «{FFFF} + 9줄×(13칸+FF01)».
  · 이름 확정 → EVE_KAN 그림을 A_FONT16 0x1FA~0x1FF 로 복사(EVE_NAME 0x11D8), 세이브엔 그림째 저장 → EVE_KAN 한글 그림 = 대사 이름.
바꾸는 것:
  · EVE_KAN: 한자 1수준 자리(0x582~)에 KS X 1001 한글 2,350자(같은 순서), 빈 9줄(0x2F0~)에 초성 19자(머리).
  · 漢字 표 → 한글 2,350자 초성 19묶음(한 줄 12자, 묶음 끝 줄 10~12칸 = ← → END) 209줄 + 상수.
  · ひらがな/カタカナ → «가~사»/«아~하» 반절표 87자씩(코드네임·조마 이름도 한글, 대사 글꼴 칸 배정에 넣음).
"""
import os, struct, itertools, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kfont

KS = [bytes([r, c]).decode('euc-kr') for r in range(0xB0, 0xC9) for c in range(0xA1, 0xFF)]     # 2,350
CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
SYL0, LAB0 = 0x582, 8 * 94                                            # 한글 음절 / 초성 머리 EVE_KAN 번호
ARROWS = (0x68, 0x67, 0x1F7)
KAN_TAB, KAN_ROWS0 = 0x6D54, 271
HIRA, KATA = 0x88DA, 0x89C4
HIRA_S, KATA_S = 0x6A56, 0x6B56
POOL_TOP, POOL_N, POOL_END, POOL_FIRST, POOL_LAST = (0x1B66, 0x1BE6, 0x1F2E, 0x20F2), 0x1F2A, 0x20EE, 0x20F0, 0x1F2C

# 반절표(하스피 2026-11-26 «성씨 말고 히라가나 가타가나는 아이우에오 식으로 · 나눠서»): 줄 = 자음, 열 = ㅏㅑㅓㅕㅗ | ㅛㅜㅠㅡㅣ
CHO_I = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'


def syl(c, v): return chr(0xAC00 + (CHO_I.index(c) * 21 + JUNG.index(v)) * 28)


def page_syllables():
    V = 'ㅏㅑㅓㅕㅗㅛㅜㅠㅡㅣ'
    a = [syl(c, v) for c in 'ㄱㄴㄷㄹㅁㅂㅅ' for v in V] + list('개내대래매배새게네데' + '레메베세와워위')
    b = [syl(c, v) for c in 'ㅇㅈㅊㅋㅌㅍㅎ' for v in V] + list('애재채캐태패해에제체' + '케테페헤의왜외')
    assert len(a) == 87 and len(b) == 87 and len(set(a)) == 87 and len(set(b)) == 87, (len(a), len(b))
    return a, b


def grid_rows(syl):
    """조마 이름 짓기(DGC_CMP·GOMADEN) 가나판 9줄 문자열 — «　»+5+«　»+5+«　», 끝 줄은 5+«　»+2"""
    q = list(syl); out = []
    for r in range(9):
        a = ''.join(q.pop(0) for _ in range(5)); bb = ''.join(q.pop(0) for _ in range(5 if r < 8 else 2))
        out.append('　' + a + '　' + bb + '　' * (13 - 7 - len(bb)))
    assert not q and all(len(x) == 13 for x in out)
    return out


NAME_SYL = set(page_syllables()[0]) | set(page_syllables()[1])       # 빌더: 대사 글꼴 칸 배정에 넣음(코드네임용 대사 코드)


def sidx(ch): return SYL0 + KS.index(ch)


def kan_glyph(ch):
    """EVE_KAN 용 글자 = 대사 글꼴 그림을 한 열 왼쪽으로(1~14열) — 이름 입력 화면은 15열을 다음 글자 왼쪽 끝으로 넘겨 찍는다(원본 한자 1~13열, 2026-11-26 «글리프에 찌꺼기» ㅏ 가로획 점)"""
    rows = struct.unpack('>16H', kfont.glyph16(ch)); assert not any(r & 0x8000 for r in rows), ch
    return struct.pack('>16H', *[(r << 1) & 0xFFFF for r in rows])


def build_kan(kan):
    k = bytearray(kan)
    assert all(x == 0 for x in k[LAB0 * 32:(LAB0 + len(CHO)) * 32]), '초성 머리 자리가 비어 있지 않음'
    for n, ch in enumerate(KS): k[(SYL0 + n) * 32:(SYL0 + n + 1) * 32] = kan_glyph(ch)
    for n, ch in enumerate(CHO): k[(LAB0 + n) * 32:(LAB0 + n + 1) * 32] = kan_glyph(ch)
    return bytes(k)


def kan_rows():
    rows = []
    for ci, grp in itertools.groupby(KS, key=lambda s: (ord(s) - 0xAC00) // 588):
        g = [sidx(c) for c in grp]; chunks = [g[i:i + 12] for i in range(0, len(g), 12)]
        if len(chunks[-1]) > 9: chunks.append([])
        for j, ch in enumerate(chunks):
            r = [LAB0 + ci if j == 0 else 0] + ch + [0] * (12 - len(ch))
            if j == len(chunks) - 1: r[10:13] = ARROWS
            rows.append(r)
    return rows


def gcode(k): return bytes([0xC0 | (k >> 6), 0x80 | (k & 0x3F)])


def fill_page(b, vtab, stab, syl, kmap, keep):
    """값 표 9×13 · 대사 코드 표 — 1~5·7~11칸에 음절(화살표 칸 그대로), 나머지 빈칸"""
    q = list(syl); sp = gcode(keep['　'])
    assert b[stab:stab + 2] == b'\xff\xff', '대사 코드 표 머리'
    for r in range(9):
        for c in range(13):
            vo = vtab + (r * 13 + c) * 2; so = stab + 2 + (r * 14 + c) * 2
            v = struct.unpack('>H', b[vo:vo + 2])[0]
            if v in ARROWS: continue
            if (1 <= c <= 5 or 7 <= c <= 11) and q:                    # 두 덩어리 5칸씩 전부(원래 빈칸 포함)
                ch = q.pop(0); b[vo:vo + 2] = struct.pack('>H', sidx(ch)); b[so:so + 2] = gcode(kmap[ch])
            else:
                b[vo:vo + 2] = b'\0\0'; b[so:so + 2] = sp
        assert b[stab + 2 + (r * 14 + 13) * 2:stab + 2 + (r * 14 + 14) * 2] == (b'\xff\x00' if r == 8 else b'\xff\x01'), ('줄 끝', r)
    assert not q, '남은 음절 %d' % len(q)


def build_name(name, kmap, keep):
    b = bytearray(name)
    rows = kan_rows(); N = len(rows); assert N <= KAN_ROWS0, N
    # 원본 확인
    assert struct.unpack('>H', b[POOL_N:POOL_N + 2])[0] == 0x10F and struct.unpack('>H', b[POOL_END:POOL_END + 2])[0] == 0xDD0
    assert struct.unpack('>H', b[POOL_FIRST:POOL_FIRST + 2])[0] == 0x11B and struct.unpack('>H', b[POOL_LAST:POOL_LAST + 2])[0] == 0xC3B
    for p in POOL_TOP: assert struct.unpack('>H', b[p:p + 2])[0] == 0x106, hex(p)
    assert b[KAN_TAB:KAN_TAB + 4] == bytes.fromhex('011b0582') and KAN_TAB + KAN_ROWS0 * 26 == HIRA
    tab = b''.join(struct.pack('>13H', *r) for r in rows)
    b[KAN_TAB:HIRA] = tab + bytes(HIRA - KAN_TAB - len(tab))
    for p in POOL_TOP: b[p:p + 2] = struct.pack('>H', N - 9)
    b[POOL_N:POOL_N + 2] = struct.pack('>H', N)
    b[POOL_END:POOL_END + 2] = struct.pack('>H', (N + 1) * 13)
    b[POOL_FIRST:POOL_FIRST + 2] = struct.pack('>H', LAB0)
    b[POOL_LAST:POOL_LAST + 2] = struct.pack('>H', LAB0 + len(CHO) - 1)
    a, c = page_syllables()
    fill_page(b, HIRA, HIRA_S, a, kmap, keep)
    fill_page(b, KATA, KATA_S, c, kmap, keep)
    return bytes(b)


def preview(kan, out):
    """한글 쪽 처음 3화면 + 성씨·이름 쪽 그림(검토용)"""
    from PIL import Image
    rows = kan_rows()
    def glyph(img, idx, x0, y0, col):
        for y in range(16):
            w = struct.unpack('>H', kan[idx * 32 + y * 2: idx * 32 + y * 2 + 2])[0]
            for x in range(16):
                if w & (0x8000 >> x): img.putpixel((x0 + x, y0 + y), col)
    pages = [rows[0:9], rows[9:18], rows[18:27]]
    a, c = page_syllables()
    for syl in (a, c):
        it = iter(syl); pg = []
        for r in range(9):
            pg.append([0] + [sidx(next(it)) if (cc != 6 and cc != 12 and not (r == 8 and cc >= 9)) else 0 for cc in range(1, 13)])
            if r == 8: pg[-1][9:12] = ARROWS
        pages.append(pg)
    img = Image.new('RGB', (len(pages) * (13 * 18 + 12), 9 * 20 + 8), (16, 40, 40))
    for p, pg in enumerate(pages):
        for r, row in enumerate(pg):
            for cc, v in enumerate(row):
                if v: glyph(img, v, p * (13 * 18 + 12) + cc * 18 + 4, r * 20 + 4, (90, 200, 255) if cc == 0 else (255, 255, 255))
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST); img.save(out)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    ROOT = os.path.dirname(HERE)
    kan = build_kan(open(os.path.join(ROOT, 'work', 'disc1', 'EVE_KAN.BIN'), 'rb').read())
    print('한글 줄 %d · 가~사·아~하 쪽 음절 %d/%d' % (len(kan_rows()), *map(len, page_syllables())))
    out = os.path.join(ROOT, 'work', 'name', '이름입력_한글판_미리보기.png'); preview(kan, out); print(out)

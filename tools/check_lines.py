# -*- coding: utf-8 -*-
r"""줄 넘침 검사기(2026-11-25, 하스피 «줄넘침 검사기 만들어» · «스샷으로 18자 맞는지 재봐»)
  창 크기 = 받은 스샷 39장 화소 실측(배율 5.359 = 320px 화면) + 원문 통계 대조:
   · 대사창(EVENT·TALK*·I_SHOP*·GOMADEN·DGP_BFP 메일) 안쪽 294px, 글자 16px 간격 → 한 줄 18자, 3줄.
     3번째 줄 마지막 칸(272~288px)은 ▼ 넘김 표시가 덮음 → 3번째 줄 17자(원문 3줄째 18자 0줄, 17자 770줄).
   · 한 줄짜리 메시지(선택지·장소 이름 등, {FF01}{FF02}{FF03} 없음): 선택지 3개 이상이면 두 칸(칸마다 8자),
     2개면 한 칸 16자 → 한계 max(원문 폭, 8).
   · A_01 설명창(아이템·스킬, 여러 줄 메시지) 18자 2줄 — 줄 2 의 「>」 포함(스샷 아이템·전투마법).
   · 전투 동료 말(DVL_BAT1) 오른쪽 창 151px → 9자(원문 9자 줄 408개). 그 밖 제자리 파일 = 원문 줄 폭·줄 수 그대로.
   원문이 한계보다 넓은 메시지는 그 원문 폭까지 허용.
  폭: 글꼴 칸 글자 1, 반각 공백 ' ' 0.5(1바이트 0x20), {FF..} 0(⚠이름 변수 {FF81} 등도 0 — 원문과 같은 셈),
      {XXX} 글꼴 칸 1. 줄 = {FF01}, 쪽 = {FF02}·{FF03}·{FF00}.
  이름 변수 폭(2026-11-25 실측, 하스피 «이름 최대 길이도 재서 넣어») — 원문·번역 양쪽 다 이 폭으로 셈:
   · {FF80} 코드네임 8 — 세이브 RAM 버퍼 9칸(hospi+FF00×4 = 8자+끝), 기본값 ???????? 8자
   · {FF81} 이름 3 · {FF82} 성 3 — 이름 입력 화면 밑줄 3+3칸, RAM 3칸+FF00(글꼴 칸 0x1FA~0x1FF 에 실행 중 그림)
   · {FF90}{FF98}{FF87} 악마 이름 = A_01 악마 표(H001447~H001804) 최대 폭(원문 8, 번역 들어오면 번역 쪽도)
   · {FF91}{FF86} 종족 = A_01 종족 표(H001386~H001439) 최대 폭(원문 3)
   · {FF99} 횟수 = DVL_BAT1 코드(0x060719E8, 2026-11-25 역어셈블)가 문자열 칸 9(0x060B6F38)에 만듦:
       센 수 n(0x7F 마스크) ≤1 → 안 씀 · n ≤ 49(성격 6 은 99) → 숫자 1~2자(1바이트 0x30+ = 반각, 폭 0.5 — 글 찍기 0x0606B2A4: 1바이트는 x+1·2바이트 글자는 x+2, 반 칸 단위)
       + 성격별 접미어(풀 0x0609458C, H007736~H007750 + S00016 「回」) · 넘치면 성격별 문구(H007751~H007766 いっぱい 등)
       → 폭 = max(1 + 접미어 최대, 넘침 문구 최대) — 원문 5(숫자 2자 1칸 + 人ぐれぇ/人くらい 4), 번역 들어오면 번역 쪽도
   · {FF84}{FF85} 전화 음성 효과·{FF92} 정렬 방식·{FF93}~{FFA3} 장비 수치 = 0(원문 폭 한계 파일이라 양쪽 같은 셈).
  python tools/check_lines.py → work/check/줄넘침.tsv — 0 줄이어야 빌드 통과(빌더가 overflow() 를 부름)"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
TOKEN = re.compile(r'\{(FF[0-9A-F]{2}|[0-9A-F]{3})\}')


VAR = {'FF80': 8, 'FF81': 3, 'FF82': 3, 'FF99': 5}
SUFFIX = ['H%06d' % k for k in range(7736, 7751)] + ['S00016']; OVER = ['H%06d' % k for k in range(7751, 7767)]
DEMON = ('FF90', 'FF98', 'FF87'); RACE = ('FF91', 'FF86')
NUMVAR = re.compile(r'\{FF(9[3-6]|A[1-3])\}')


def table_width(rows, a, b):
    """A_01 표(id a~b) 최대 폭. rows = [(id, 원문, 번역)]"""
    w = 0
    for i, ja, ko in rows:
        if a <= i <= b:
            for t in (ja, ko):
                P = pages(t) if t else []
                if P: w = max(w, width(P[0][0], t is ko))
    return w


def set_vars(rows):
    """rows = [(id, 원문, 번역)] (A_01·DVL_BAT1) → 악마·종족·횟수 폭 갱신"""
    d = table_width(rows, 'H001447', 'H001804'); r = table_width(rows, 'H001386', 'H001439')
    for k in DEMON: VAR[k] = d
    for k in RACE: VAR[k] = r
    ids = lambda L: [(i, j, k) for i, j, k in rows if i in L]
    VAR['FF99'] = max(1 + table_width(ids(SUFFIX), '', 'Z'), table_width(ids(OVER), '', 'Z'))
    return dict(VAR)


def init_vars(tr):
    ko = {r['id']: r['ko'] for r in tr}
    base = [l.split('\t') for l in open(os.path.join(ROOT, 'data', 'sh_ja.tsv'), encoding='utf-8').read().splitlines()[1:]]
    seq = {}
    for r in base:
        if r[4] or not (r[1] == 'EVENT.BIN' or r[1].startswith(DLG) or r[1] in ('GOMADEN.EVE', 'DGP_BFP.BIN')): continue
        seq.setdefault(r[1], []).append((int(r[2], 16), r[5]))
    for f, L in seq.items():                                          # 이어진 한 줄 메시지 묶음(선택지) 크기
        L.sort(); grp = []
        for pos, t in L + [(None, '{FF01}')]:
            if pos is not None and not re.search(r'\{FF0[123]\}', t) and not TOKEN.sub('', t).rstrip().endswith(('?', '。', '!', '…', '」')) and not t.startswith('>'):
                grp.append(pos); continue
            if 1 <= len(grp) <= 2: PAIR.update((f, q) for q in grp)
            grp = []
    RACE_JA.update(r[5] for r in base if r[1] == 'A_01.BIN' and 'H001386' <= r[0] <= 'H001439')
    HELP_JA.update(r[5] for r in base if r[1] == 'DGC_CMP.BIN' and 0x304EC <= int(r[2], 16) < 0x359CE)
    v = set_vars([(r[0], r[5], ko.get(r[0], '')) for r in base if r[1] in ('A_01.BIN', 'DVL_BAT1.BIN')])
    print('이름 변수 폭:', ' '.join('%s=%g' % kv for kv in sorted(v.items())))


# 번역의 부호·숫자 = 1바이트 반각(2026-11-26 하스피 «부호 숫자 반각으로 넣어») — 글꼴 0x20~0x7F 칸 오른쪽 8px, x+1(반 칸).
#   원문(ja) 의 같은 글자는 전각 칸(판독표가 ASCII 로 적음)이라 폭 1. 반각 그림 있는 부호·숫자만(@ ^ ` { | } ~ 는 그림 없음 → 전각).
HALF_SET = '!"#$%&' + "'" + '()*+,-./0123456789:;<=>?'
HALF = {c: c for c in HALF_SET}
HALF.update({chr(0xFF01 + ord(c) - 0x21): c for c in HALF_SET})   # 전각으로 쳐도 반각으로


def width(s, half=False):
    """half=True = 번역 글(부호·숫자 반각 0.5)"""
    w = 0.0; i = 0
    while i < len(s):
        m = TOKEN.match(s, i)
        if m:
            v = m.group(1); w += VAR.get(v, 0) if v.startswith('FF') else 1; i = m.end(); continue
        w += 0.5 if s[i] == ' ' or (half and s[i] in HALF) else 1; i += 1
    return w


def pages(t):
    """[[줄 글, …], …] — 이름 괄호 토큰은 지우고 글자만 남김"""
    out = []
    for pg in re.split(r'\{FF0[023]\}', t):
        lines = pg.split('{FF01}')
        lines = [x for x in lines if TOKEN.sub(lambda m: '' if m.group(1).startswith('FF') else 'x', x) != '']
        if lines: out.append(lines)
    return out


DLG = ('TALK', 'I_SHOP')


RACE_JA = set(); HELP_JA = set(); PAIR = set()                      # init_vars 가 채움 · PAIR = 2개 이하 선택지 묶음의 (파일, 위치)
CUR = [None]                                                         # 지금 검사하는 줄 (파일, 위치) — 부르는 쪽이 넣음
WIN18 = ('GOMADEN.BIN', 'KYU_PET.BIN', 'DGC_CMP.BIN', 'INS.BIN', 'INST.BIN', 'DZ_ST.BIN', 'DGN_3DD.BIN', 'EVE_NAME.BIN',
         'M01LINK.BIN', 'M02LINK.BIN', 'M03LINK.BIN', 'M04LINK.BIN', 'M05LINK.BIN', 'M06LINK.BIN', '9_TITLE.BIN', 'A_TITLE.BIN')


def kind(f, ja):
    """화면 종류(2026-11-26 스샷 실측·원문 통계로 정함):
       대사 = 대사창 18·18·17×3줄(쪽 추가 가능) · 한줄 = 대사 파일의 한 줄(원문 8 이하면 선택지 두 칸 8, 넘으면 16)
       설명 = A_01 설명창 18×2 · 이름 = A_01 목록 이름 8 · 종족 = 애널라이즈 종족 칸 4
       창18 = 메뉴·합체·의뢰·지도 등 여러 줄 메시지(18자, 줄 수는 원문까지 — 쪽 추가 없음)
       전투 = DVL_BAT1 여러 줄(원문 줄 9.5 이하면 동료 말 창 9, 아니면 18 · 줄 수 원문까지)
       도움 = DGC_CMP 도움말 표(0x304EC 묶음) 한 줄 18 · 목록 = 그 밖 한 줄(최소 8 — 목록·선택지 칸 실측 8) · 원문 = 원문 폭"""
    multi = re.search(r'\{FF0[123]\}', ja)
    if f == 'EVENT.BIN' or f.startswith(DLG) or f in ('GOMADEN.EVE', 'DGP_BFP.BIN'): return '대사' if multi else '한줄'
    if f == 'A_01.BIN' and '{FF01}' in ja and not NUMVAR.search(ja): return '설명'
    if f == 'A_01.BIN' and '{FF01}' in ja: return '설명수치'
    if f == 'A_01.BIN' and ja in RACE_JA: return '종족'
    if f == 'A_01.BIN' and not multi and not ja.startswith(('>', '」', '{')): return '이름'
    if f == 'DVL_BAT1.BIN' and multi: return '전투'
    if (f.startswith('M0') and 'LINK' in f) and '{FF03}' in ja: return '대사'      # 지도 묶음 마을 사람 대사 = 대사창(쪽 넘김 있음)
    if f in WIN18 and multi: return '창18'
    if f == 'DGC_CMP.BIN' and ja in HELP_JA: return '도움'
    if not multi and f != 'A_01.BIN': return '목록'
    return '원문'


def limits(f, ja):
    """(줄마다 한계 [1줄, 2줄, 3줄…], 쪽 줄 수 한계)"""
    P = pages(ja); lw = max([width(x) for p in P for x in p] or [0]); pl = max([len(p) for p in P] or [1])
    k = kind(f, ja)
    if k == '대사':
        l3 = [width(p[2]) for p in P if len(p) > 2]                # 원문 3번째 줄 폭(17 넘는 원문만 늘림) — 예전 max(18,…) 로 늘 18 이 돼 ▼ 칸에 마침표가 밀렸다(2026-11-27 코요테 «모양이군.»)
        return [max(18, lw), max(18, lw), max([17] + l3)] + [max(18, lw)] * 8, max(3, pl)
    if k == '한줄':
        t = TOKEN.sub('', ja).rstrip()
        if t.startswith('>') or t.endswith(('?', '。', '!', '…', '」')): return [max(18, lw)] * 10, max(1, pl)   # 물음·혼잣말 = 대사창 한 줄
        if CUR[0] in PAIR: return [max(16, lw)] * 10, max(1, pl)     # 선택지 2개 = 한 칸 16(스샷 선택지 (2))
        return [max(8 if lw <= 8 else 16, lw)] * 10, max(1, pl)
    if k == '설명': return [max(18, lw)] * 10, max(2, pl)
    if k == '설명수치':                                               # 첫 줄 = 수치 변수 줄(원문 폭), 둘째 줄부터 설명창 18
        first = ja.split('{FF01}')[0]
        if not TOKEN.sub(lambda m: '' if m.group(1).startswith('FF') else 'x', first): return [max(18, lw)] * 10, max(2, pl)   # 첫 줄이 변수뿐 → 줄 셈에서 빠짐
        w0 = max([width(p[0]) for p in P] or [0]); return [w0] + [max(18, lw)] * 9, max(2, pl)
    if k == '이름': return [max(8, lw)] * 10, max(1, pl)            # 아이템·장비·마법 목록 이름 칸 8칸(스샷 아이템·장비·전투마법 실측, 2026-11-26)
    if k == '종족': return [max(4, lw)] * 10, 1                       # 애널라이즈 종족 칸(邪鬼 160px → 이름 510px = 4칸)
    if k == '창18': return [max(18, lw)] * 10, pl
    if k == '전투': return [max(9 if lw <= 9.5 else 18, lw)] * 10, pl
    if k == '도움': return [max(18, lw)] * 10, pl
    if k == '목록':
        t = TOKEN.sub('', ja).rstrip(' 　')
        if not t.startswith(('{',)) and re.search(r'(\?|ません|ください|下さい|します|ますか|。)$', t) and not ja.startswith(('{FF1B}', '{FF16}')):
            return [max(18, lw)] * 10, pl                              # 확인·안내 메시지 = 위 설명창·메시지 창 18
        if f == 'M00_2D.BIN' and CUR[0] is not None and 0x2E1F2 <= CUR[0][1] < 0x2E224:
            return [4] * 10, pl                                        # 지도 이동 목록 = 4칸(스샷 «시바하마» 꽉 참, 2026-11-27 «아카네다이·아마미 베이 넘침»)
        if f == 'M00_2D.BIN' and CUR[0] is not None and 0x2E16C <= CUR[0][1] < 0x2E1D6:
            return [8] * 10, pl                                        # 지도 상점 목록 = 8칸(스샷 «생체 에너지 협회» 딱 맞음, 2026-11-26 하스피 «칸넘침»)
        if f in ('M00_2D.BIN',) or f.startswith('M0') and 'LINK' in f:
            return [max(12, lw)] * 10, pl                              # 지명 상자 = 글자에 맞춰 커짐(스샷 맵 «天海市あかね台» 상자 딱 맞음), 12 로 둠
        return [max(8, lw)] * 10, pl
    return [lw] * 10, pl


FILL = re.compile(r'[ 　]{2,}|　+')


def fit_fill(ja, ko):
    """칸 맞춤 공백(원문 줄의 공백 2칸 이상·전각 공백 덩어리)을 원문 줄 폭에 맞춰 늘이고 줄임 — 줄 끝 기호 자리 유지.
       원문 줄에 채움이 없으면 그대로. 줄마다({FF01} 단위), 쪽 구분 그대로."""
    jl = re.split(r'(\{FF0[0-3]\})', ja); kl = re.split(r'(\{FF0[0-3]\})', ko)
    if len(jl) != len(kl): return ko
    out = []
    for a, b in zip(jl, kl):
        if a.startswith('{FF0') or not FILL.search(TOKEN.sub('', a)) or not FILL.search(b): out.append(b); continue
        target = width(a); m = list(FILL.finditer(b))[-1]               # 마지막 채움 덩어리를 조정
        if TOKEN.sub('', b[m.end():]).strip(' ~}') or TOKEN.sub('', a[list(FILL.finditer(a))[-1].end():] if FILL.search(a) else 'x').strip(' ~}'):
            out.append(b); continue                                     # 줄 끝 채움(뒤에 표시 기호만)일 때만 — 글 사이 «  » 는 그대로
        rest = width(b[:m.start()] + b[m.end():], True)
        need = target - rest
        ma = list(FILL.finditer(TOKEN.sub('', a)))[-1].group(0)          # 원문 채움이 반각이면 반각으로
        if set(ma) == {' '}: fill = ' ' * int(round(max(0, need) * 2))
        else:
            n_full = int(max(0, need)); fill = '　' * n_full + (' ' if (max(0, need) - n_full) >= 0.5 else '')
        out.append(b[:m.start()] + fill + b[m.end():])
    return ''.join(out)


def overflow(f, row_ja, row_ko):
    """[(쪽, 줄, 폭, 한계, 줄 글)] — 넘친 것만"""
    L, pl = limits(f, row_ja); bad = []
    for pi, p in enumerate(pages(row_ko)):
        if len(p) > pl: bad.append((pi + 1, 0, len(p), pl, '쪽 줄 수'))
        for li, x in enumerate(p):
            w = width(x, True); lim = L[min(li, len(L) - 1)]
            if w > lim: bad.append((pi + 1, li + 1, w, lim, TOKEN.sub(lambda m: '‹%s›' % m.group(1) if m.group(1) in VAR else '', x)))
    return bad


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import build
    rows, src = build.tr_rows(); init_vars(rows); out = ['id\t파일\t쪽\t줄\t폭\t한계\t내용']
    for r in rows:
        for pg, ln, w, lim, x in overflow(r['file'], r['ja'], r['ko']):
            out.append('%s\t%s\t%d\t%d\t%g\t%g\t%s' % (r['id'], r['file'], pg, ln, w, lim, x))
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'check', '줄넘침.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('번역 줄 %d · 넘침 %d → work/check/줄넘침.tsv' % (len(rows), len(out) - 1))
    for l in out[1:21]: print('  ' + l)


if __name__ == '__main__':
    main()


# ───────── 자동 줄바꿈(2026-11-25 하스피 «자동 줄바꿈도 넣어») ─────────
#  대상: 대사(대사창 18·18·17자 3줄 쪽)·설명(A_01 18자 2줄, 쪽 나눔 없음). 넘치는 쪽만 손댐 — 안 넘치는 쪽은 글자 하나 안 바꿈.
#  번역자가 넣은 {FF01} 은 «꼭 끊는 자리»로 두고, 넘치는 줄만 어절(반각 공백) 경계에서 다시 끊음(끊는 자리의 공백 = {FF01} 로 바뀜).
#  어절 하나가 한 줄보다 길면 글자 단위로 끊음. 3줄 넘으면 «내용 안 깎고» 쪽을 하나 더 만듦: 줄 끝 {FF01}{FF03}{FF02}(원문과 같은 쪽 넘김).
PAGE_END = re.compile(r'(?:\{FF01\})*(?:\{FF0[023]\})+')


def _units(line):
    """줄 → [(조각 글, 폭)] — 글자·토큰 단위"""
    out = []; i = 0
    while i < len(line):
        m = TOKEN.match(line, i)
        if m: out.append(m.group(0)); i = m.end()
        else: out.append(line[i]); i += 1
    return out


PUNCT = ',.!?:;)]}' + "'" + '"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'


def squeeze(ja, ko):
    """전프로젝트 규칙: 문장부호 바로 뒤 공백 1칸(반각·전각) 지움 — 2칸 이상은 채움이라 둠.
       원문부터 부호 뒤 공백이 있는 줄은 «값 써 넣는 칸»일 수 있어 안 건드림."""
    pat = '([' + re.escape(PUNCT) + '])[ 　](?![ 　])'
    talk = CUR[0] is not None and kind(CUR[0][0], ja) in ('대사', '창18', '전투', '도움', '한줄')   # 대사·창 글은 원문에 «。　» 가 있어도 지움(2026-11-26 하스피 «왜 문장부호 뒤에 띄어쓰기가 있어»)
    if not talk and re.search(pat, TOKEN.sub('', ja)): return ko                    # 표·목록의 «값 써 넣는 칸»만 원문대로
    if talk:                                                                        # 대사: 부호와 공백 사이 폭 없는 코드(멈춤 FF04·FF06, 색 FF16~FF1C)도 건너뜀 — «흥…{FF06} 이렇게»
        ko = re.sub(r'([' + re.escape(PUNCT) + r'])((?:\{FF0[46]\}|\{FF1[6-9A-C]\})+)[ 　](?![ 　])', lambda m: m.group(1) + m.group(2), ko)
    parts = re.split(r'(\{(?:FF[0-9A-F]{2}|[0-9A-F]{3})\})', ko)          # 토큰 밖 글에만(토큰 닫는 } 를 부호로 보지 않음)
    return ''.join(x if TOKEN.fullmatch(x) else re.sub(pat, lambda m: m.group(1), x) for x in parts)


def _wrap_line(line, lims):
    """한 줄(번역자 줄) → 여러 줄. lims(k) = k 번째로 만들 줄의 한계.
       끊는 자리 = 공백(공백은 줄바꿈으로 바뀜) 또는 문장부호 바로 뒤. 끊을 자리가 없으면 «안 끊고» 넘친 채 돌려줌(검사기가 잡음 —
       글자 단위로 잘라 넣는 폴백 금지)."""
    out = []; rest = line
    while True:
        lim = lims(len(out))
        if width(rest, True) <= lim: out.append(rest); return out
        u = _units(rest); acc = 0.0; brk = None                         # brk = (자르는 자리, 공백이면 True)
        for k, x in enumerate(u):
            acc += width(x, True)
            if acc > lim:
                if x == ' ': brk = (k, True)
                break
            if x == ' ' and k > 0: brk = (k, True)
            elif x in PUNCT and k + 1 < len(u) and u[k + 1] != ' ': brk = (k + 1, False)
        if not brk: out.append(rest); return out
        k, sp = brk
        out.append(''.join(u[:k])); rest = ''.join(u[k + 1 if sp else k:])


GLUE_NEXT = re.compile(r'^(?:습니다|답니다|니다|어요|아요|에요|예요|이에요|지요|죠|다|요|는|은|을|를|이|가|의|에|로|와|과|도|만|까지|부터|라|고|며|면|서|게|지)(?![가-힣])|^(?:습니다|답니다|니다)')


def _join(a, b):
    """번역자 줄바꿈을 풀 때: 부호 뒤면 붙임(부호 뒤 공백 규칙), 다음 줄이 어미·조사로 시작하면 낱말 가운데 끊긴 것이라 붙임, 그 밖은 띄어 씀"""
    a2 = TOKEN.sub('', a).rstrip(); b2 = TOKEN.sub('', b).lstrip()
    if not a2 or not b2: return a + b
    if a2[-1] in PUNCT or a2[-1] in '「『【(（' : return a + b
    if '가' <= a2[-1] <= '힣' and GLUE_NEXT.match(b2): return a + b
    return a + ' ' + b


def push_down(lines, lim):
    """lines(번역자 줄) 중 넘치는 줄: 한계에 맞게 자르고 나머지를 «다음 줄 앞»에 붙인다(다음 줄이 빈 줄·없음이면 새 줄). 빈 줄에서 멈춤."""
    out = list(lines); i = 0
    while i < len(out):
        while out[i] and width(out[i], True) > lim(i) and i > 0 and out[i - 1] and (i + 1 >= len(out) or not out[i + 1]):
            m = re.match(r'(\S+) (.*)$', out[i])                    # 넘친 줄이 단락 끝이면 앞 낱말을 윗줄로 끌어올림(윗줄 한계 안에서)
            if not m: break
            up = _join(out[i - 1], m.group(1))
            if width(up, True) > lim(i - 1): break
            out[i - 1], out[i] = up, m.group(2)
        if out[i] and width(out[i], True) > lim(i):
            pieces = _wrap_line(out[i], lambda j: lim(i + j))
            if len(pieces) > 1:
                rest = pieces[1:]; out[i] = pieces[0]
                tail = ' '.join(rest) if len(rest) > 1 else rest[0]
                if i + 1 < len(out) and out[i + 1]: out[i + 1] = _join(tail, out[i + 1])
                else: out.insert(i + 1, tail)
        i += 1
    return out


SENT_END = '.!?…」』~～♪)）'
VARTOK = re.compile(r'\{FF[89A][0-9A-F]\}')


def _glue(a, b):
    a2 = TOKEN.sub('', a).rstrip()
    return a + b if (a2 and a2[-1] in PUNCT) else a + ' ' + b


def balance2(s, l1, l2):
    """한 줄 s 를 두 줄로 — 끊는 자리(공백·부호 뒤) 중 두 줄 폭의 큰 쪽이 가장 작은 곳. 못 끊으면 None"""
    u = _units(s); best = None
    for i in range(1, len(u)):
        if u[i] == ' ': a, b = ''.join(u[:i]), ''.join(u[i + 1:])
        elif u[i - 1] in PUNCT and u[i] != ' ': a, b = ''.join(u[:i]), ''.join(u[i:])
        else: continue
        wa, wb = width(a, True), width(b, True)
        if not TOKEN.sub('', a).strip() or not TOKEN.sub('', b).strip() or wa > l1 or wb > l2: continue
        if best is None or max(wa, wb) < best[0]: best = (max(wa, wb), a, b)
    return [best[1], best[2]] if best else None


def _fix_tails(pages, L, pl):
    """대사 쪽 나눔 뒤 «문장 꼬리만 떨어진» 자리 고르기(2026-11-27 하스피 «안고쳐진게 더 있을꺼 아냐» — 전수 검사 A 46·B 34)
       A: 새 쪽이 짧은 꼬리(폭 8 이하·줄 2 이하·변수 없음)이고 앞 쪽 끝이 문장 끝이 아니면 → 앞 쪽 마지막 줄 + 꼬리를 새 쪽으로, 한 줄(18) 안 되면 두 줄로 고르게.
       B: 쪽 안에서 3칸 이하 꼬리 줄(앞 줄이 문장 끝 아님) → 앞 줄과 합쳐 두 줄로 고르게."""
    vis = lambda s: TOKEN.sub('', s).strip()
    for pk in range(1, len(pages)):
        t, prev = pages[pk], pages[pk - 1]
        if not t or len(t) > 2 or len(prev) < 2 or any(VARTOK.search(x) for x in t + prev[-1:]): continue
        if width(vis(''.join(t)), True) > 8 or not vis(prev[-1]) or vis(prev[-1])[-1] in SENT_END: continue
        s = prev[-1]
        for x in t: s = _glue(s, x)
        new = [s] if width(s, True) <= L[0] else balance2(s, L[0], L[1])
        if new: prev.pop(); pages[pk] = new
    for p in pages:
        for j in range(1, len(p)):
            if VARTOK.search(p[j]) or VARTOK.search(p[j - 1]): continue
            if width(vis(p[j]), True) > 3 or not vis(p[j - 1]) or vis(p[j - 1])[-1] in SENT_END: continue
            nb = balance2(_glue(p[j - 1], p[j]), L[min(j - 1, len(L) - 1)], L[min(j, len(L) - 1)])
            if nb: p[j - 1], p[j] = nb
    return [p for p in pages if p]


def lift_third(lines, L):
    """대사 쪽 3줄에서 3번째 줄만 ▼ 칸(17) 넘침 → 3번째 줄 앞 낱말을 2번째 줄 끝으로(2번째가 넘치면 그 앞 낱말을 1번째로) 올림.
       외톨이 낱말 쪽을 만들지 않는 첫 수단(2026-11-27). 안 되면 None."""
    if len(lines) != 3 or not all(lines): return None
    out = list(lines)
    for _ in range(12):
        if width(out[2], True) <= L[2]:
            return out if all(width(out[i], True) <= L[i] for i in range(3)) else None
        m = re.match(r'(\S+) (.*)$', out[2])
        if not m: return None
        out[1] = _join(out[1], m.group(1)); out[2] = m.group(2)
        while width(out[1], True) > L[1]:
            m = re.match(r'(\S+) (.*)$', out[1])
            if not m: return None
            out[0] = _join(out[0], m.group(1)); out[1] = m.group(2)
            if width(out[0], True) > L[0]: return None
    return None


def reflow(f, ja, ko):
    k = kind(f, ja)
    if k not in ('대사', '설명', '창18', '전투') or not ko: return ko
    L, pl = limits(f, ja)
    out = []; pos = 0
    ends = list(PAGE_END.finditer(ko))
    segs = []; p0 = 0
    for m in ends: segs.append((ko[p0:m.start()], m.group(0))); p0 = m.end()
    if p0 < len(ko): segs.append((ko[p0:], ''))
    for body, end in segs:
        lines = body.split('{FF01}')
        ok = not overflow(f, ja, body + end)                  # 검사기와 같은 판정(빈 줄 셈 방식까지 같게)
        if ok or not body: out.append(body + end); continue
        if k == '대사' and pl == 3:
            lt = lift_third(lines, L)
            if lt and not overflow(f, ja, '{FF01}'.join(lt) + end): out.append('{FF01}'.join(lt) + end); continue
            if len(lines) == 3 and all(lines) and width(lines[0], True) <= L[0] and width(lines[1], True) <= L[1] \
                    and width(lines[2], True) <= L[0]:                 # 못 올리면 3번째 줄 «통째로» 다음 쪽 첫 줄로(낱말 하나만 넘어가는 쪽 막기)
                nb = lines[0] + '{FF01}' + lines[1] + '{FF01}{FF03}{FF02}' + lines[2]
                if not overflow(f, ja, nb + end): out.append(nb + end); continue
        if k in ('설명', '창18', '전투'):
            new = []
            for x in lines: new += _wrap_line(x, lambda j, b=len(new): L[min(b + j, len(L) - 1)])
            out.append('{FF01}'.join(new) + end); continue
        lines = push_down(lines, lambda j: L[min(j % pl, len(L) - 1)])     # 넘친 꼬리를 다음 줄 앞에 붙여 다시 맞춤(외톨이 낱말 줄 막기, 2026-11-26 하스피 «병신 줄바꿈»)
        pages = [[]]
        for x in lines:
            cur = len(pages[-1]) % pl if pages[-1] else 0
            pieces = _wrap_line(x, lambda j: L[min((len(pages[-1]) + j) % pl, len(L) - 1)])
            if 0 < len(pages[-1]) < pl and len(pieces) > 1 and len(pages[-1]) + len(pieces) > pl:   # 한 줄이 쪽 경계에서 갈라지면(외톨이 낱말 쪽) 그 줄 통째로 다음 쪽 첫 줄부터(2026-11-27)
                p2 = _wrap_line(x, lambda j: L[min(j % pl, len(L) - 1)])
                if len(p2) <= pl: pages.append([]); pieces = p2
            for piece in pieces:
                if len(pages[-1]) >= pl: pages.append([])
                pages[-1].append(piece)
        for pk in range(1, len(pages)):                                # 새로 생긴 쪽에 한두 글자만 넘어가면 앞쪽 마지막 줄을 같이 넘김(2026-11-27 하스피 «한두글자나 문장부호가 넘쳐서 창넘김으로 통째로»)
            vis = TOKEN.sub('', '{FF01}'.join(pages[pk])).replace('{FF01}', '').strip()   # (변수 k 를 쓰면 위 종류 k 를 덮어 다음 쪽부터 종류 판정이 깨졌다)
            if vis and width(vis, True) <= 4 and len(pages[pk - 1]) >= 2 and len(pages[pk]) < pl:
                pages[pk].insert(0, pages[pk - 1].pop())
                a, b = pages[pk][0], pages[pk][1]                      # 넘긴 줄과 꼬리를 한 줄로(18 안이면) — «현재 / 불명.» 막기(2026-11-27)
                a2 = TOKEN.sub('', a).rstrip(); j = a + b if (a2 and a2[-1] in PUNCT) else a + ' ' + b
                if width(j, True) <= L[0]: pages[pk][0:2] = [j]
                continue
            if k == '대사' and len(pages[pk - 1]) == pl and pages[pk] and width(TOKEN.sub('', pages[pk][0]), True) <= 8:
                a, b = pages[pk - 1][-1], pages[pk][0]                 # 앞 쪽 마지막 줄 꼬리만 넘어온 짧은 첫 줄 → 그 줄 통째로 다음 쪽 첫 줄(2026-11-27 «마침표만 다음 창»)
                a2 = TOKEN.sub('', a).rstrip()
                j = a + b if (a2 and a2[-1] in PUNCT) else a + ' ' + b
                if width(j, True) <= L[0] and not (len(pages[pk]) > 1 and width(pages[pk][1], True) > L[1]):
                    pages[pk - 1].pop(); pages[pk][0] = j
        if k == '대사': pages = _fix_tails(pages, L, pl)
        out.append('{FF01}{FF03}{FF02}'.join('{FF01}'.join(p) for p in pages) + end)
    return ''.join(out)

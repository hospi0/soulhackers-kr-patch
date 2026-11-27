# -*- coding: utf-8 -*-
r"""소울 해커즈 빌더 v2 (2026-11-25 — v1 하스피 «번역중이니까 빌더 ㄱ», v2 «1번부터 ㄱ 자동 줄바꿈도 넣어»)
  번역 = data/tr/*.tsv (없으면 work/tsv/*.tsv) — 열 id·파일·위치·바이트·원문·번역. 번역 빈칸 = 원문 바이트 그대로.
  글 → 바이트: 한글 = data/kmap.json 칸(tools/kfont.assign, 가나·한자 칸 덮음), 부호·영숫자 = 원래 칸(kfont.tables keep),
             {FFxx} = 제어 바이트, {XXX}(16진 3자리) = 그 글꼴 칸 그대로, 반각 공백 = 1바이트 0x20, 전각 공백 = 칸 0x140,
             부호·숫자 !"#$%&'()*+,-./0-9:;<=>? (전각으로 쳐도) = 1바이트 반각(0.5칸, 2026-11-26).
  자동 줄바꿈(check_lines.reflow): 넘치는 대사 쪽만 어절 경계에서 {FF01}, 3줄 넘으면 {FF01}{FF03}{FF02} 로 쪽 추가(내용 안 깎음)
     → 바뀐 줄 목록 work/check/자동줄바꿈.tsv. 그 뒤 줄 넘침 검사(대사 18·18·17·선택지 8·설명 18×2·전투 9) — 남으면 중단.
  토큰 검사: 원문과 번역의 {FF..} 순서가 같아야 함(줄바꿈 FF01·창 넘김 FF02/FF03 은 자유) — 어기면 빌드 중단.
  .EVE 형식(머리 0008·스크립트·메시지 위치표(u16, 본문 기준)·본문): 본문 다시 쓰고 위치표 고침(본문 64 KB 한계).
  EVENT.BIN = 덩어리 표(EVE_MAIN.BIN 0x24470·EVE_TM.BIN 0x1CB50, 24 B×34 = 위치 u32·크기 u32·이름 16, 2026-11-25 코드 확인)
     → 덩어리마다 다시 쓰고 섹터 정렬로 차례 재배치, 두 표 고침. 게임은 덩어리를 RAM 0x240000 에 (크기>>11)+1 섹터 읽음.
  크기 상한(= 같은 버퍼에 원래 실리는 가장 큰 것, 그 이상은 RAM 미확인): EVENT 덩어리 0x10800(VR_TOWN) · TALK* 0x13800(TALK02,
     RAM 0x270000) · I_SHOP* 0x2800(I_SHOP01) · GOMADEN.EVE 0x4800(자기 크기).
  디스크: 위 파일(EVENT.BIN·TALK*·I_SHOP*·GOMADEN.EVE)은 «항상» 트랙 1 끝 고정 자리(SLOTS 순서·칸 크기 고정 — 빌드마다 LBA 같음)로 옮김.
     트랙 1 = 원래 마지막 파일 뒤(DS2_BIB 다음)에 자리 1,157 섹터 끼우고 뒤 2초(150) 빈 섹터 다시 만듦 → 트랙 2(오디오)는 그대로,
     CDDA1 디렉터리 LBA·PVD 볼륨 크기 +1,157. 그 밖 파일: 제자리(번역 바이트 ≤ 원문, 남는 자리 0x00).
  글꼴: A_FONT16.BIN 한글 칸 덮기. 디스크 두 장 모두(텍스트 파일 두 장 같음 — 다르면 중단).
  python tools/build.py             → 검사만(디스크 안 씀) — 번역 0줄이면 «결과 = 원본» 되돌림 검산
  python tools/build.py --write [--install]   ⛔하스피 허락 받고"""
import glob, hashlib, os, re, shutil, struct, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import kfont
from check_lines import HALF
from iso import Disc, ROMS
from cdrom_ecc import recalc_sector
D1 = os.path.join(ROOT, 'work', 'disc1')
F_DIR = r'F:\hospi\roms\ss roms\Devil Summoner - Soul Hackers (Japan) (Disc %02d)'
TOK = re.compile(r'\{(FF[0-9A-F]{2}|[0-9A-F]{3})\}')
FREE_TOK = {'FF01', 'FF02', 'FF03'}


class BuildError(Exception): pass


def tr_rows():
    src = sorted(glob.glob(os.path.join(ROOT, 'data', 'tr', '*.tsv'))) or sorted(glob.glob(os.path.join(ROOT, 'work', 'tsv', 'sh_*.tsv')))
    rows = []
    for f in src:
        for l in open(f, encoding='utf-8').read().splitlines()[1:]:
            p = l.split('\t')
            if len(p) >= 6 and p[5].strip(): rows.append(dict(id=p[0], file=p[1], pos=int(p[2], 16), n=int(p[3]), ja=p[4], ko=p[5]))
    return rows, src


TOKEN_FREE_ID = {'H002694'}                                          # 기본 이름 誠{1FE} → 세이고(吾 칸 {1FE} 안 씀, 2026-11-26 하스피 «아이 세이고»)


def tokens(t):
    """원문과 같아야 하는 토큰 = 제어 {FFxx}(줄·쪽 넘김 빼고) + 이름 글자 칸 {1FA}~{1FF}. 그 밖 {XXX}(장음 {1F4} 등 글자 칸)는 자유"""
    xs = [x for x in TOK.findall(t) if x not in FREE_TOK and (x.startswith('FF') or 'FA' <= x[1:] <= 'FF' and x[0] == '1')]
    var = lambda x: x[:3] in ('FF8', 'FF9', 'FFA')                      # 이름·종족·수 변수 = 우리말 어순 따라 순서 바뀜 허용(개수만), 제어 코드는 순서까지(2026-11-26)
    return [x for x in xs if not var(x)] + sorted(x for x in xs if var(x))


def encode(t, kmap, keep):
    out = bytearray(); i = 0
    while i < len(t):
        m = TOK.match(t, i)
        if m:
            v = m.group(1)
            out += bytes([0xFF, int(v[2:], 16)]) if v.startswith('FF') else code(int(v, 16)); i = m.end(); continue
        ch = t[i]; i += 1
        if ch == ' ': out += b' '; continue                          # 반각 공백 = 1바이트 0x20(반 칸, 원문도 씀 — 대사창 18자 안에 더 들어감)
        if ch in HALF: out += HALF[ch].encode(); continue           # 부호·숫자 = 1바이트 반각(2026-11-26, 모든 글 모듈 같은 찍기 코드 — 0x20~0x7F 오른쪽 8px)
        if kfont.is_ko(ch): k = kmap[ch]
        elif ch in keep: k = keep[ch]
        else: raise BuildError('글꼴에 없는 글자 %r' % ch)
        out += code(k)
    return bytes(out)


def code(k): return bytes([0xC0 | k >> 6, 0x80 | (k & 0x3F)])


def eve_header(b, at=0):
    if len(b) < at + 8: return None
    h = struct.unpack_from('>4H', b, at)
    return h if h[0] == 8 and 8 <= h[1] <= h[2] <= h[3] <= len(b) - at else None


def rebuild_eve(blob, reps, cap, name):
    """blob = .EVE 한 덩어리(0 부터). reps = [(덩어리 안 위치, 원래 길이, 새 바이트)]. 본문 다시 쓰고 위치표 고침."""
    _, a, b, c = eve_header(blob)
    body = blob                                                        # 정확한 크기(덩어리 표·파일 크기) — 끝 0 자르지 않음
    n_tab = (c - b) // 2
    if n_tab == 0:                                                     # 메시지 없는 덩어리
        if reps: raise BuildError('위치표 없는 덩어리에 번역 줄 %s' % name)
        return blob
    tab = list(struct.unpack_from('>%dH' % n_tab, blob, b))
    text = body[c:]; reps = sorted((p - c, n, nb) for p, n, nb in reps if p >= c)
    out = bytearray(); cur = 0; shift = []                            # (원래 위치, 새 위치 − 원래 위치)
    delta = 0
    for p, n, nb in reps:
        assert p >= cur, ('겹친 줄', name, hex(p + c))
        out += text[cur:p]; shift.append((p, delta)); out += nb; delta += len(nb) - n; cur = p + n
    out += text[cur:]
    def mp(o):
        d = 0
        for p, dd in shift:
            if o > p:
                if o < p + next(n for q, n, nb in reps if q == p): raise BuildError('위치표가 줄 가운데를 가리킴 %s %X' % (name, o + c))
                d = dd + (len(next(nb for q, n, nb in reps if q == p)) - next(n for q, n, nb in reps if q == p))
        return o + d
    new_tab = [mp(o) if (o or i == 0) else 0 for i, o in enumerate(tab)]
    if max(new_tab) > 0xFFFF: raise BuildError('본문 64 KB 넘음 %s' % name)
    nb = bytearray(blob[:c]); struct.pack_into('>%dH' % n_tab, nb, b, *new_tab); nb += out
    if len(nb) > cap: raise BuildError('크기 넘침 %s %d > %d (버퍼 상한)' % (name, len(nb), cap))
    return bytes(nb)


EV_TABLES = [('EVE_MAIN.BIN', 0x24470), ('EVE_TM.BIN', 0x1CB50)]     # EVENT.BIN 덩어리 표 사본 두 곳(같은 내용)
N_EV = 34
CAP_EV = 0x10800
CAP = {'TALK': 0x13800, 'I_SHOP': 0x2800, 'GOMADEN.EVE': 0x4800}
# 트랙 1 끝 고정 자리(이 순서·칸 크기는 바꾸지 말 것 — 빌드마다 같은 LBA, 옛 스테이트가 새 디스크에서 빈칸 읽지 않게)
SLOTS = [('EVENT.BIN', 474)] + [('TALK%02X.EVE' % k, 39) for k in range(16)] + \
        [('I_SHOP.EVE', 5)] + [('I_SHOP%02d.EVE' % k, 5) for k in range(1, 10)] + [('GOMADEN.EVE', 9), ('A_01.BIN', 32)]
# 위치표(u16) 문자열 파일: 이름 → (표 위치, 기준, 크기 상한). A_01 = RAM 0x210000, 뒤 0x21B6F6~0x220000 비어 있음
#   (스테이트 8장 모두 0 · 이 범위 가리키는 코드 리터럴 없음, 0x220000 부터 GOMADEN·KENCPK 가 씀, 2026-11-26)
INDEXED = {'A_01.BIN': (0x8, 0xE88, 0x10000)}
SLOT_TOTAL = sum(n for _, n in SLOTS)                                # 1,189 섹터
POSTGAP = 150


def cap_of(f):
    for k, v in CAP.items():
        if f.startswith(k): return v
    return None


def ev_table():
    m = open(os.path.join(D1, 'EVE_MAIN.BIN'), 'rb').read(); t = []
    for k in range(N_EV):
        o = 0x24470 + 24 * k; off, sz = struct.unpack_from('>II', m, o); t.append((off, sz, m[o + 8:o + 24]))
    for fn, at in EV_TABLES:
        assert open(os.path.join(D1, fn), 'rb').read()[at:at + 24 * N_EV] == m[0x24470:0x24470 + 24 * N_EV], ('덩어리 표 사본 다름', fn)
    return t


def build_event(b, L):
    """EVENT.BIN 다시 쓰기 → (새 파일, 새 표 [(위치, 크기, 이름)])"""
    t = ev_table(); out = bytearray(); new = []
    for k, (off, sz, nm) in enumerate(t):
        blob = b[off:off + sz]; name = nm.split(b'\0')[0].decode()
        reps = [(p - off, n, x) for p, n, x, _ in L if off <= p < off + sz]
        if k == 0:                                                    # EVENT.TBL(디렉터리) — 번역 없음
            assert not reps; nb = blob
        else: nb = rebuild_eve(blob, reps, CAP_EV, 'EVENT.BIN:' + name)
        pos = len(out); assert pos % 0x800 == 0
        new.append((pos, len(nb), nm)); out += nb + bytes((-len(nb)) % 0x800)
    return bytes(out), new


def patch_ev_tables(newfiles, tab):
    for fn, at in EV_TABLES:
        d = bytearray(newfiles.get(fn) or open(os.path.join(D1, fn), 'rb').read())
        for k, (pos, sz, nm) in enumerate(tab): struct.pack_into('>II', d, at + 24 * k, pos, sz); d[at + 24 * k + 8:at + 24 * k + 24] = nm
        newfiles[fn] = bytes(d)


def rebuild_indexed(b, L, tab, base, cap, name):
    """u16 위치표(기준 base) 문자열 파일 다시 쓰기. L = [(파일 위치, 원래 길이, 새 바이트, id)]"""
    n = (base - tab) // 2; idx = list(struct.unpack_from('>%dH' % n, b, tab))
    starts = [base + x for x in idx] + [len(b)]
    out = bytearray(b[:base]); new = []; reps = sorted((p, m, x) for p, m, x, _ in L)
    k = 0
    for i in range(n):
        a0, a1 = starts[i], starts[i + 1]
        if a1 < a0: raise BuildError('위치표 순서 아님 %s %d' % (name, i))
        new.append(len(out) - base); seg = bytearray(); cur = a0
        while k < len(reps) and reps[k][0] < a1:
            p, m, x = reps[k]
            if p < cur or p + m > a1: raise BuildError('줄이 문자열 경계를 넘음 %s %X' % (name, p))
            seg += b[cur:p] + x; cur = p + m; k += 1
        seg += b[cur:a1]; out += seg
    if max(new) > 0xFFFF: raise BuildError('위치 64 KB 넘음 %s' % name)
    struct.pack_into('>%dH' % n, out, tab, *new)
    if len(out) > cap: raise BuildError('크기 넘침 %s %d > %d (RAM 상한)' % (name, len(out), cap))
    return bytes(out)


# 코드 모듈 속 위치표 문자열 묶음(tools/strtab.py 로 찾음, 모듈 적재 0x06030000 — 표 기준 리터럴이 맞아떨어짐으로 확인)
TABLE_MODS = ['DGC_CMP.BIN', 'KYU_PET.BIN', 'GOMADEN.BIN', 'DVL_BAT1.BIN', 'INS.BIN', 'A_LOGO.BIN', 'A_TITLE.BIN', 'DZ_ST.BIN',
              'M00_2D.BIN', 'INST.BIN', '9_TITLE.BIN', '9_LOAD.BIN', 'DGB_MAP.BIN']
MOD_BASE = 0x06030000
POOL_RAM = 0x00210000                                                # A_01.BIN 뒤에 붙여 실음(상한 INDEXED A_01)
_BLK = {}


def blocks(f, b):
    """[(표, 기준, 칸 값들, 끝 표시 있음, 끝, 기준 리터럴 자리들)] — 겹치는 것·3칸 미만 뺌"""
    if f in _BLK: return _BLK[f]
    import strtab
    res = []
    for t, base, n, refs in strtab.tables(b, MOD_BASE):
        v = list(struct.unpack_from('>%dH' % n, b, t)); sent = 0
        if len(v) >= 2 and v[-1] == 0 and v[-2] == 0xFFFF: v = v[:-2]; sent = 2   # FFFF + 0000 채움
        elif v[-1] == 0xFFFF: v = v[:-1]; sent = 1
        if len(v) < 3: continue
        res.append((t, base, v, sent, strtab.block_end(b, base, v), refs))
    res.sort(key=lambda x: x[1]); ok = []
    for x in res:
        if any(not (x[4] <= y[1] or y[4] <= x[1]) or not (x[0] + 2 * len(x[2]) + 2 * x[3] <= y[1] or y[4] <= x[0]) for y in res if y is not x): continue
        ok.append(x)
    _BLK[f] = ok
    return ok


FFFF_ = bytes([0xFF, 0xFF])


def rebuild_block(b, base, v, end, reps, name):
    starts = [base + x for x in v] + [end]; new = []; out = bytearray(); k = 0
    for i in range(len(v)):
        a0, a1 = starts[i], starts[i + 1]; new.append(len(out)); cur = a0
        while k < len(reps) and reps[k][0] < a1:
            p, m, x = reps[k]
            if p < cur or p + m > a1: raise BuildError('줄이 문자열 경계를 넘음 %s %X' % (name, p))
            out += b[cur:p] + x; cur = p + m; k += 1
        out += b[cur:a1]
    if max(new) > 0xFFFF: raise BuildError('묶음 64 KB 넘음 %s' % name)
    return bytes(out), new


# DGP_BFP.BIN: 대사 덩어리 512개가 0x4000 + k×0x8000 고정 자리(앞 0x4000 = 다른 자료). 덩어리 뒤 ~ 구역 끝은 0.
#   제자리에서 다시 쓰기(위치 고정이라 표 고칠 것 없음), 상한 = 가장 큰 원본 덩어리 0x3174(2026-11-26).
FIXED_EVE = {'DGP_BFP.BIN': (0x4000, 0x8000, 0x4000, 0x3174)}       # 첫 자리, 간격, 구역 크기, 상한


# 묶음 파일 속에 박힌 대사 덩어리(M01~06LINK 각 1개 — 지도 이름·마을 대사, RAM 0x06066000 에 묶음째). 위치 고정, 제자리(원래 끝 + 뒤 0 여유) 안에서만.
EMBED_EVE = ['M01LINK.BIN', 'M02LINK.BIN', 'M03LINK.BIN', 'M04LINK.BIN', 'M05LINK.BIN', 'M06LINK.BIN']
_EMB = {}


def embedded(f, b):
    """[(덩어리 시작, 끝, 상한)]"""
    if f in _EMB: return _EMB[f]
    res = []
    for o in range(0, len(b) - 8, 2):
        h = struct.unpack_from('>4H', b, o)
        if h[0] != 8 or not (8 < h[1] < h[2] < h[3] < 0x8000) or o + h[3] >= len(b): continue
        n = (h[3] - h[2]) // 2
        if n < 8: continue
        tab = struct.unpack_from('>%dH' % n, b, o + h[2])
        nz = [t for t in tab[1:] if t]                                   # 0 칸 = 빈 자리(M05·M06 끝 칸)
        if tab[0] != 0 or any(a > c for a, c in zip(nz, nz[1:])): continue
        tab = [0] + nz
        if sum(1 for t in tab[1:] if b[o + h[3] + t - 2:o + h[3] + t] == bytes([0xFF, 0])) < 0.7 * (n - 1): continue
        e = b.find(bytes([0xFF, 0]), o + h[3] + max(tab)) + 2; j = e
        while j < len(b) and b[j] == 0: j += 1
        res.append((o, e, j - o))
    _EMB[f] = res
    return res


def chunk_len(b, o, zone):
    t = b[o:o + zone].rstrip(b'\x00')
    return len(t) + (1 if t.endswith(bytes([0xFF])) else 0)


def inplace_cap(b, p, n):
    """제자리 한도 = 원래 길이 + 바로 뒤 4바이트 정렬 채움 0(문자열이 4바이트 정렬로 놓인 곳 — A_TITLE 기본 이름 등)"""
    e = p + n; k = e
    while k % 4 and k < len(b) and b[k] == 0: k += 1
    return n + (k - e if k % 4 == 0 else 0)


def direct_refs(f, b, p, n):
    """(메시지 시작, 끝, 시작을 가리키는 직접 포인터 자리들) — 코드 모듈만"""
    st = b.rfind(bytes([0xFF, 0]), 0, p); st = st + 2 if st >= 0 and p - st < 80 else p
    en = b.find(bytes([0xFF, 0]), p + n - 2) + 2
    if f not in TABLE_MODS or en <= p: return st, en, []
    for q in (p, st):                                                # 줄 시작 또는 메시지 시작을 가리키는 것
        pat = struct.pack('>I', MOD_BASE + q); refs = []; k = b.find(pat)
        while k >= 0:
            if k % 4 == 0: refs.append(k)
            k = b.find(pat, k + 1)
        if refs: return q, en, refs
    return st, en, []


def build_files(rows, kmap, keep):
    files = {}
    def get(f):
        if f not in files: files[f] = open(os.path.join(D1, f), 'rb').read()
        return files[f]
    byf = defaultdict(list); errs = []; skipped = []
    for r in rows:
        if r['file'] in INDEXED and r['pos'] < INDEXED[r['file']][1]: skipped.append(r['id']); continue   # 위치표 영역 잡음
        if r['file'].endswith('.EVE'):                                # .EVE 스크립트 영역(본문 앞) 줄 = 명령 바이트 잡음(14줄) → 넣지 않음
            h = eve_header(get(r['file']))
            if h and r['pos'] < h[3]: skipped.append(r['id']); continue
        if tokens(r['ja']) != tokens(r['ko']) and r['id'] not in TOKEN_FREE_ID and r['ja'] != '誠{1FE}{FF00}': errs.append('토큰 다름 %s %s' % (r['id'], r['ko'][:30])); continue
        try: nb = encode(r['ko'], kmap, keep)
        except BuildError as e: errs.append('%s %s' % (r['id'], e)); continue
        byf[r['file']].append((r['pos'], r['n'], nb, r['id']))
    out = {}; pool = bytearray(); pool_fix = []; ev_tab = None                      # 넘친 묶음 → A_01 뒤(POOL_RAM)
    for f in [x for x in byf if x in TABLE_MODS]:
        b = get(f); nb = bytearray(b); rest = []
        for t, base, v, sent, end, refs in blocks(f, b):
            fx = [(p + 2, m - 2, x[2:]) for p, m, x, _ in byf[f] if p == base - 2 and b[p:p + 2] == FFFF_ and x[:2] == FFFF_]   # 첫 줄을 표 끝 FFFF 째 추출한 것(2026-11-26 전투 설정 «戦闘中メッセージ» 원문 남음)
            reps = sorted([(p, m, x) for p, m, x, _ in byf[f] if base <= p < end] + fx)
            if not reps: continue
            try: blk, new = rebuild_block(b, base, v, end, reps, '%s@%X' % (f, base))
            except BuildError as e: errs.append(str(e)); continue
            if len(blk) <= end - base:                                # 제자리
                nb[base:end] = blk + bytes(end - base - len(blk))
            else:                                                     # A_01 뒤로 옮기고 기준 리터럴 고침
                if len(pool) % 2: pool += b'\x00'
                pool_fix.append((f, refs, len(pool))); pool += blk
            struct.pack_into('>%dH' % len(new), nb, t, *new)
        done = {(p) for t, base, v, sent, end, refs in blocks(f, b) for p, m, x, i in byf[f] if base <= p < end or (p == base - 2 and b[p:p + 2] == FFFF_ and x[:2] == FFFF_)}
        byf[f] = [x for x in byf[f] if x[0] not in done]
        files[f] = bytes(nb)
        if files[f] != b or any(x[0] == f for x in pool_fix): out[f] = files[f]
    for f, L in byf.items():
        b = get(f)
        try:
            if f == 'EVENT.BIN':
                out[f], ev_tab = build_event(b, L)                     # 위치표는 반복 끝에서(EVE_TM·EVE_MAIN 번역 줄이 뒤에 원본에서 다시 써 덮던 버그, 2026-11-26 새 게임 크래시)
            elif f in INDEXED:
                out[f] = rebuild_indexed(b, L, *INDEXED[f], f)
            elif f in EMBED_EVE:
                nb = bytearray(b); left = list(L)
                for o, e, cap in embedded(f, b):
                    reps = [(p - o, m, x) for p, m, x, _ in left if o <= p < e]
                    if not reps: continue
                    left = [x for x in left if not (o <= x[0] < e)]
                    blk = rebuild_eve(b[o:e], reps, cap, '%s@%X' % (f, o)); nb[o:o + cap] = blk + bytes(cap - len(blk))
                for p, m, x, i in left:
                    if len(x) > m: raise BuildError('제자리 넘침 %s %s %d > %d' % (i, f, len(x), m))
                    nb[p:p + m] = x + bytes(m - len(x))
                out[f] = bytes(nb)
            elif f in FIXED_EVE:
                first, step, zone, cap = FIXED_EVE[f]; nb = bytearray(b)
                for o in range(first, len(b), step):
                    reps = [(p - o, m, x) for p, m, x, _ in L if o <= p < o + zone]
                    if not reps: continue
                    n0 = chunk_len(b, o, zone); blk = rebuild_eve(b[o:o + n0], reps, cap, '%s@%X' % (f, o))
                    nb[o:o + zone] = blk + bytes(zone - len(blk))
                out[f] = bytes(nb)
            elif eve_header(b) and f.endswith('.EVE'):
                c_ = eve_header(b)[3]; inner = [(p, n, x) for p, n, x, _ in L if p >= c_]; outside = [(p, n, x, i) for p, n, x, i in L if p < c_]
                nb = bytearray(rebuild_eve(b, inner, cap_of(f) or (len(b) + 2047) // 2048 * 2048, f))
                for p, n, x, i in outside:
                    if len(x) > n: raise BuildError('제자리 넘침 %s %s %d > %d' % (i, f, len(x), n))
                    nb[p:p + n] = x + bytes(n - len(x))
                out[f] = bytes(nb)
            else:
                nb = bytearray(b)
                for p, n, x, i in L:
                    if n < len(x) <= inplace_cap(b, p, n): n = inplace_cap(b, p, n)
                    if len(x) > n:                                    # 문자열 시작을 가리키는 직접 포인터(4바이트 정렬 u32 = 0x06030000+시작)가 있으면 A_01 뒤로 옮김
                        st, en, refs = direct_refs(f, b, p, n)
                        if refs:
                            msg = b[st:p] + x + b[p + n:en]
                            if len(pool) % 2: pool += bytes(1)
                            pool_fix.append((f, refs, len(pool))); pool += msg; continue
                        raise BuildError('제자리 넘침 %s %s %d > %d' % (i, f, len(x), n))
                    nb[p:p + n] = x + bytes(n - len(x))
                out[f] = bytes(nb)
        except BuildError as e: errs.append(str(e))
    if ev_tab: patch_ev_tables(out, ev_tab)
    for f in TABLE_MODS:                                              # 표 묶음만 바뀐 모듈
        if f in files and files[f] != open(os.path.join(D1, f), 'rb').read() and f not in out: out[f] = files[f]
    if pool:
        a = bytearray(out.get('A_01.BIN') or get('A_01.BIN')); a += bytes((-len(a)) % 4); at = POOL_RAM + len(a); a += pool
        if len(a) > INDEXED['A_01.BIN'][2]: errs.append('A_01 + 옮긴 묶음 %d > %d (RAM 상한)' % (len(a), INDEXED['A_01.BIN'][2]))
        out['A_01.BIN'] = bytes(a)
        for f, refs, off in pool_fix:
            m = bytearray(out[f])
            for r in refs: struct.pack_into('>I', m, r, at + off)
            out[f] = bytes(m)
        print('  옮긴 묶음 %d개 %d 바이트 → A_01 뒤 RAM %X~%X' % (len(pool_fix), len(pool), at, at + len(pool)))
    if skipped: print('  스크립트 영역 줄 건너뜀 %d (잡음): %s' % (len(skipped), ' '.join(skipped[:8])))
    return out, errs


def roundtrip():
    """번역 없이 다시 쓰기 → 원본과 같은지(위치표·본문·EVENT 재배치·표 검산)"""
    bad = []
    for f in glob.glob(os.path.join(D1, '*.EVE')):
        b = open(f, 'rb').read()
        if eve_header(b) and rebuild_eve(b, [], 1 << 20, f) != b: bad.append(os.path.basename(f))
    for f, prm in INDEXED.items():
        b = open(os.path.join(D1, f), 'rb').read()
        if rebuild_indexed(b, [], *prm, f) != b: bad.append(f)
    for f in EMBED_EVE:
        b = open(os.path.join(D1, f), 'rb').read()
        for o, e, cap in embedded(f, b):
            if rebuild_eve(b[o:e], [], cap, f) != b[o:e]: bad.append('%s@%X' % (f, o))
    for f, (first, step, zone, cap) in FIXED_EVE.items():
        b = open(os.path.join(D1, f), 'rb').read()
        for o in range(first, len(b), step):
            if eve_header(b, o):
                n0 = chunk_len(b, o, zone)
                if rebuild_eve(b[o:o + n0], [], cap, f) != b[o:o + n0]: bad.append('%s@%X' % (f, o))
    for f in TABLE_MODS:
        b = open(os.path.join(D1, f), 'rb').read()
        for t, base, v, sent, end, refs in blocks(f, b):
            blk, new = rebuild_block(b, base, v, end, [], f)
            if blk != b[base:end] or new != v: bad.append('%s 묶음 %X' % (f, base))
    e = open(os.path.join(D1, 'EVENT.BIN'), 'rb').read(); ne, tab = build_event(e, [])
    if ne != e[:len(ne)] or e[len(ne):].strip(b'\0'): bad.append('EVENT.BIN 재배치')
    if [x[:2] for x in tab] != [x[:2] for x in ev_table()]: bad.append('EVENT 표')
    return bad


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''): h.update(c)
    return h.hexdigest()


def bcd(x): return (x // 10) << 4 | (x % 10)


def mode1_sector(lba, data):
    m = lba + 150; hdr = bytes([bcd(m // 4500), bcd(m // 75 % 60), bcd(m % 75), 1])
    return recalc_sector(b'\x00' + b'\xff' * 10 + b'\x00' + hdr + data + bytes(288))


def write_disc(n, newfiles):
    D = Disc(n); out_dir = os.path.join(ROOT, 'dist', 'build', 'disc%d' % n); os.makedirs(out_dir, exist_ok=True)
    src_dir = os.path.dirname(ROMS[n]); t1 = os.path.join(out_dir, os.path.basename(ROMS[n]))
    for f in os.listdir(src_dir):
        q = os.path.join(src_dir, f)
        if f != os.path.basename(ROMS[n]): shutil.copyfile(q, os.path.join(out_dir, f))
    files = {p.strip('/'): (l, s) for p, l, s in D.files}
    nsec = os.path.getsize(ROMS[n]) // 2352
    base = max(l + (s + 2047) // 2048 for l, s in files.values() if l < nsec)      # 트랙 1 안 마지막 파일 끝 = 끼울 자리
    tail = D.f; tail.seek(base * 2352); gap = tail.read((nsec - base) * 2352)
    assert nsec - base == POSTGAP and all(gap[k * 2352 + 16:k * 2352 + 2064] == bytes(2048) for k in range(POSTGAP)), ('트랙 끝 빈 섹터 아님', n, base, nsec)
    slot = {}; at = base
    for nm, k in SLOTS: slot[nm] = (at, k); at += k
    dirty = set()
    with open(ROMS[n], 'rb') as src, open(t1, 'wb') as fh:
        src.seek(0); left = base * 2352
        while left:
            c = src.read(min(left, 1 << 24)); fh.write(c); left -= len(c)
        for lba in range(base, base + SLOT_TOTAL + POSTGAP): fh.write(mode1_sector(lba, bytes(2048)))

    def put(fh, lba, data):
        for i in range(0, len(data), 2048):
            fh.seek((lba + i // 2048) * 2352); sec = bytearray(fh.read(2352)); assert sec[15] == 1
            new = data[i:i + 2048].ljust(2048, b'\0')
            if sec[16:2064] == new: continue                        # 같은 섹터는 다시 계산 안 함(56MB MESS 파일 9분 → 수 초, 2026-11-27)
            sec[16:2064] = new; fh.seek((lba + i // 2048) * 2352); fh.write(recalc_sector(bytes(sec))); dirty.add(lba + i // 2048)

    def dirrec(fh, name, lba=None, size=None):
        rl, ro = D.record(name); fh.seek(rl * 2352); sec = bytearray(fh.read(2352))
        if lba is not None: struct.pack_into('<I', sec, 16 + ro + 2, lba); struct.pack_into('>I', sec, 16 + ro + 6, lba)
        if size is not None: struct.pack_into('<I', sec, 16 + ro + 10, size); struct.pack_into('>I', sec, 16 + ro + 14, size)
        fh.seek(rl * 2352); fh.write(recalc_sector(bytes(sec))); dirty.add(rl)
    with open(t1, 'r+b') as fh:
        for name, nb in newfiles.items():
            lba, size = files[name]
            if D.read(name) != open(os.path.join(D1, name), 'rb').read(): raise BuildError('디스크 %d 의 %s 가 1장과 다름 — 따로 처리 필요' % (n, name))
            if name in slot:                                          # 고정 자리로 옮김
                sl, k = slot[name]; assert len(nb) <= k * 2048, ('자리 넘침', name, len(nb), k * 2048)
                put(fh, sl, nb + bytes((-len(nb)) % 2048)); dirrec(fh, name, sl, len(nb))
            else:
                cap = (size + 2047) // 2048 * 2048; assert len(nb) <= cap, (name, len(nb), cap)
                old = D.sec(lba, cap // 2048); full = nb + bytes(cap - len(nb))
                for i in range(0, cap, 2048):
                    if full[i:i + 2048] != old[i:i + 2048]: put(fh, lba + i // 2048, full[i:i + 2048])
                if len(nb) != size: dirrec(fh, name, None, len(nb))
        cl, cs = files['CDDA1']; dirrec(fh, 'CDDA1', cl + SLOT_TOTAL, None)              # 트랙 2 가 뒤로 밀림
        fh.seek(16 * 2352); pvd = bytearray(fh.read(2352)); vs = struct.unpack_from('<I', pvd, 16 + 80)[0]
        struct.pack_into('<I', pvd, 16 + 80, vs + SLOT_TOTAL); struct.pack_into('>I', pvd, 16 + 84, vs + SLOT_TOTAL)
        fh.seek(16 * 2352); fh.write(recalc_sector(bytes(pvd))); dirty.add(16)
    print('  디스크 %d · 자리 LBA %d~%d(+%d 섹터) · 바뀐 섹터 %d · 트랙 01 md5 %s' % (n, base, base + SLOT_TOTAL - 1, SLOT_TOTAL, len(dirty), md5(t1)))
    return t1


def verify_disc(n, t1, newfiles):
    """구운 트랙을 다시 읽어 파일 = newfiles(그 밖 파일 = 원본) 검산"""
    import iso
    keep = iso.ROMS[n]; iso.ROMS[n] = t1
    try: D = Disc(n)
    finally: iso.ROMS[n] = keep
    bad = []                                                          # 바뀐 파일만 다시 읽어 검산(나머지는 원본 섹터 그대로 복사 — 전 파일 검산은 수 분 걸림, 2026-11-26)
    names = {p.strip('/') for p, l, s in D.files}
    for nm, want in newfiles.items():
        if nm not in names or D.read(nm) != want: bad.append(nm)
    return bad


def main():
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    import time; t0 = time.time(); st = lambda m: print('[%5.0f초] %s' % (time.time() - t0, m))
    bad = roundtrip(); print('되쓰기 검산(번역 없이 다시 쓰기 = 원본, EVENT 재배치·표 포함): %s' % ('통과' if not bad else '실패 %s' % bad[:5]))
    if bad: sys.exit(1)
    st('되쓰기 검산 끝'); rows, src = tr_rows(); print('번역 파일 %d개 · 번역된 줄 %d' % (len(src), len(rows)))
    import check_lines
    check_lines.init_vars(rows)
    wrapped = []
    for r in rows:
        check_lines.CUR[0] = (r['file'], r['pos'])
        r['ko'] = r['ko'].replace('{FF1C}~{FF16}', '\x00F\x00').replace('~', '～').replace('\x00F\x00', '{FF1C}~{FF16}')   # 번역 물결 → «～» 전용 칸(«~» 0x19E 는 ♀ 장비 표시 — 그 표시만 남김, 2026-11-27)
        r['ko'] = r['ko'].replace('{FF82}{FF81}', '{FF82} {FF81}')    # 성+이름 사이 띄어 씀(일본어는 붙여 씀 — 2026-11-27 하스피 «하스피하스피»)
        if r['file'] == 'A_01.BIN' and 'H001447' <= r['id'] <= 'H001804':   # 악마·인물 이름 표: 전투 HUD 가 이름을 u16 단위로 읽음 → 1바이트 공백이 짝을 어긋나게 해 뒤 글자가 깨짐(개리 트롯) → 전각 공백(0x140)
            r['ko'] = r['ko'].replace(' ', '　')
        r['ko'] = check_lines.squeeze(r['ja'], r['ko'])              # 부호 뒤 공백 지움(전프로젝트 규칙, 원문에 부호+공백 있으면 제외)
        r['ko'] = check_lines.fit_fill(r['ja'], r['ko'])             # 칸 맞춤 공백 = 원문 줄 폭에 맞춤
        x = check_lines.reflow(r['file'], r['ja'], r['ko'])
        if x != r['ko']: wrapped.append((r['id'], r['file'], r['ko'], x)); r['ko'] = x
        if ((r['file'] == 'A_01.BIN' and check_lines.kind(r['file'], r['ja']) in ('이름', '종족')) or (r['file'] in ('INS.BIN', 'INST.BIN') and '{FF01}' not in r['ko'])) and r['ko'].endswith('{FF00}'):   # INS·INST 에 같은 u16 짝 길이 재기(0x0603B138·0x0603115C) — 자기 문자열(파티 이름 «레이 레이호» 등)도   # 한 줄 이름: 1바이트 글자 홀수면 끝에 반각 공백 → FF00 이 짝(2바이트) 자리에 오게
            body = TOK.sub('', r['ko'])                                # (INST 0x06031124 이 이름 길이를 u16 짝으로 FF00 찾아 잼 — 어긋나면 «칸보다 길다»고 안 그림: 인스톨 이름 전부 빈칸, 2026-11-27)
            if sum(1 for ch in body if ch == ' ' or ch in HALF) % 2:
                r['ko'] = r['ko'][:-len('{FF00}')] + ' {FF00}'
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'check', '자동줄바꿈.tsv'), 'w', encoding='utf-8') as f:
        f.write('id\t파일\t번역(원래)\t자동 줄바꿈 뒤\n')
        for w in wrapped: f.write('%s\t%s\t%s\t%s\n' % w)
    print('자동 줄바꿈 %d줄 → work/check/자동줄바꿈.tsv' % len(wrapped))
    import name_entry
    hangul = {ch for r in rows for ch in r['ko'] if kfont.is_ko(ch)} | name_entry.NAME_SYL   # 이름 입력 성씨·이름 쪽 음절(코드네임용 대사 코드)
    slots, keep = kfont.tables(); print('한글 음절 %d / 칸 %d' % (len(hangul), len(slots)))
    try: kmap = kfont.assign(hangul, save='--write' in sys.argv)
    except AssertionError as e: print('⛔', e); sys.exit(1)
    ov = []
    for r in rows:
        check_lines.CUR[0] = (r['file'], r['pos']); ov += [(r['id'], x) for x in check_lines.overflow(r['file'], r['ja'], r['ko'])]
    if ov:
        for i, (pg, ln, w, lim, x) in ov[:20]: print('  ⛔줄 넘침 %s 쪽%d 줄%d 폭 %g > %g  %s' % (i, pg, ln, w, lim, x))
        print('줄 넘침 %d — 빌드 중단(자동 줄바꿈으로 못 고치는 것: 선택지·설명·전투 등)' % len(ov)); sys.exit(1)
    st('줄 검사·글꼴 배정 끝'); newfiles, errs = build_files(rows, kmap, keep); st('파일 다시 쓰기 끝')
    for e in errs[:30]: print('  ⛔', e)
    if errs: print('오류 %d — 빌드 중단' % len(errs)); sys.exit(1)
    if rows: newfiles['A_FONT16.BIN'] = kfont.build_font(kmap)
    import hud_hook                                                   # 전투 파티 칸 이름 = 16×16 한글을 2:1 로(2026-11-27)
    newfiles['A_01.BIN'], newfiles['DVL_BAT1.BIN'] = hud_hook.patch(newfiles['A_01.BIN'], newfiles['DVL_BAT1.BIN'], kfont.HUDTMP[0])
    import ins_hook                                                   # 회복 장소(INS) 반각 이름·메뉴 = 한글 가로 2:1(2026-11-27)
    newfiles['A_01.BIN'], newfiles['INS.BIN'] = ins_hook.patch(newfiles['A_01.BIN'], newfiles.get('INS.BIN') or open(os.path.join(D1, 'INS.BIN'), 'rb').read())
    assert kfont.build_font(kmap)[ins_hook.TMP * 32:ins_hook.TMP * 32 + 32] == bytes(32), 'INS 훅 임시 칸 0x13F 가 비어 있지 않음'
    import title_logo                                                 # 타이틀 로고 «데빌 서머너»(하스피 그림)·«소울 해커즈»(2026-11-27)
    newfiles['A_TITSPR.BIN'] = title_logo.patch(open(os.path.join(D1, 'A_TITSPR.BIN'), 'rb').read())
    import opening_kr                                                 # 오프닝 그림 글자(MESS.BIN = EVE_MES.BIN 사본 둘 다, 2026-11-27)
    _m = opening_kr.patch(open(os.path.join(D1, 'MESS.BIN'), 'rb').read())
    newfiles['MESS.BIN'] = _m; newfiles['EVE_MES.BIN'] = _m
    newfiles['EVE_KAN.BIN'] = name_entry.build_kan(open(os.path.join(D1, 'EVE_KAN.BIN'), 'rb').read())      # 이름 입력 한글판
    newfiles['EVE_NAME.BIN'] = name_entry.build_name(newfiles.get('EVE_NAME.BIN') or open(os.path.join(D1, 'EVE_NAME.BIN'), 'rb').read(), kmap, keep)
    for nm, _ in SLOTS:                                               # 고정 자리 파일은 번역 없어도 늘 옮김(LBA 고정)
        if nm not in newfiles: newfiles[nm] = open(os.path.join(D1, nm), 'rb').read()
    print('바뀌는 파일 %d: %s' % (len(newfiles), ' '.join(sorted(newfiles))[:300]))
    if '--write' not in sys.argv: print('검사만(디스크 안 씀)'); return
    for n in (1, 2):
        st('디스크 %d 쓰기 시작' % n); t1 = write_disc(n, newfiles); st('디스크 %d 쓰기 끝' % n)
        bad = verify_disc(n, t1, newfiles); print('  디스크 %d 다시 읽기 검산: %s' % (n, '통과' if not bad else '⛔ %s' % bad[:5]))
        if bad: sys.exit(1)
        st('디스크 %d 검산 끝' % n)
        if '--install' in sys.argv:
            dst = os.path.join(F_DIR % n, os.path.basename(ROMS[n])); assert os.path.exists(dst), dst
            shutil.copyfile(t1, dst); assert md5(dst) == md5(t1); print('  F: 설치', dst); st('디스크 %d 설치 끝' % n)


if __name__ == '__main__':
    main()

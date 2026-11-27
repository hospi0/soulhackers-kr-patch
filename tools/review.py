# -*- coding: utf-8 -*-
r"""번역 TSV 검수(2026-11-26, 하스피 «완전 초벌이야 말투 명사 인물명 토큰 줄넘침 바이트길이 선택지길이 등등 면밀히 검사해서 넣어야해»)
  입력 work/tr_in/*.tsv(my files/Download 사본) · 기준 work/tsv/sh_*.tsv(원문)
  자동 수정(기록 work/review/changes.tsv): 원문 「」『』【】 를 번역이 '' "" ‘’ “” 로 바꾼 것만 원래 괄호로 되돌림.
  검사 결과 work/review/*.tsv — 막는 것(빌드 안 됨)·볼 것(사람 판단) 구분:
    막는 것: 형식 · 토큰 · 글꼴 없는 글자 · 일본어 남음 · 줄 넘침(부호 뒤 공백 지움·자동 줄바꿈 뒤) · 바이트 초과(제자리) · 파일 크기
    볼 것  : 빈 번역 · 화자 이름 표기 여러 개 · 이름 음역(か·た행 거센소리·つ=츠) · 용어(A_01 악마·아이템·스킬·종족 번역과 다른 줄) ·
             변수 뒤 조사({FF81}가 등 이름 받침 모름) · 말투 섞임(화자별 합쇼/해요/반말 비율)
  python tools/review.py            → 보고만
  python tools/review.py --merge    → 자동 수정 반영한 번역을 data/tr/sh_*.tsv 로(⛔병합 전 data/tr 백업)"""
import collections, glob, os, re, shutil, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import check_lines as C, build as B, kfont, tr_fix
OUT = os.path.join(ROOT, 'work', 'review')
TOK = re.compile(r'\{[^}]*\}')
JP = re.compile(r'[ぁ-ゖァ-ヺ一-鿿]')
VARS = ('FF80', 'FF81', 'FF82', 'FF86', 'FF87', 'FF90', 'FF91', 'FF98')
JOSA = re.compile(r'\{(FF8[0-2]|FF8[67]|FF9[018])\}(이|가|을|를|은|는|과|와|으로|로|이랑|랑|이나|나|이야|야|아|이여|여)(?![가-힣])')


def load():
    master = {}; order = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'tsv', 'sh_*.tsv'))):
        for l in open(f, encoding='utf-8').read().splitlines()[1:]:
            p = l.split('\t'); master[p[0]] = (os.path.basename(f), p); order.append(p[0])
    tr = {}; bad = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'tr_in', '*.tsv'))):
        for l in open(f, encoding='utf-8-sig').read().splitlines()[1:]:
            p = l.split('\t')
            if len(p) < 6: bad.append(('열 수', os.path.basename(f), l[:40])); continue
            m = master.get(p[0])
            if not m: bad.append(('없는 id', p[0], '')); continue
            if m[1][1:5] != p[1:5]: bad.append(('원문 칸 바뀜', p[0], p[4][:30])); continue
            if p[0] in tr: bad.append(('id 겹침', p[0], '')); continue
            tr[p[0]] = p[5]
    return master, order, tr, bad


def fix_brackets(ja, ko):
    """원문 괄호 수만큼 '…'/"…"/‘…’/“…” 쌍을 원래 괄호로(앞에서부터)"""
    for o, c in (('「', '」'), ('『', '』'), ('【', '】')):
        need = ja.count(o) - ko.count(o)
        while need > 0:
            m = re.search(r"'([^']*)'|\"([^\"]*)\"|‘([^’]*)’|“([^”]*)”", ko)
            if not m: break
            ko = ko[:m.start()] + o + next(g for g in m.groups() if g is not None) + c + ko[m.end():]; need -= 1
    return ko


def speaker(t):
    m = re.match(r'\{FF19\}【([^】]*)】\{FF16\}', t)
    return m.group(1) if m else None


def style(sent):
    s = re.sub(r'[\s.!?…‥~♪」』)"\'？！。、,]+$', '', TOK.sub('', sent))
    if not s: return None
    if re.search(r'(습니다|습니까|십시오|ㅂ니다|입니다|입니까|합니다|합니까|됩니다|됩니까)$', s): return '합쇼'
    if s.endswith('요'): return '해요'
    return '반말'


HK = {'カ': '카', 'キ': '키', 'ク': '쿠', 'ケ': '케', 'コ': '코', 'タ': '타', 'テ': '테', 'ト': '토', 'ツ': '츠', 'チ': '치'}
HK.update({k.translate(str.maketrans('カキクケコタテトツチ', 'かきくけこたてとつち')): v for k, v in HK.items()})


def main():
    sys.stdout.reconfigure(encoding='utf-8'); os.makedirs(OUT, exist_ok=True)
    for x in glob.glob(os.path.join(OUT, '*.tsv')): os.remove(x)
    master, order, tr, bad = load()
    changes = []; skip = set(); man = tr_fix.manual()
    for i in list(tr):
        ja = master[i][1][4]; ko = tr[i]
        if ja in tr_fix.DEFAULT_NAME and ko != tr_fix.DEFAULT_NAME[ja]: changes.append((i, '주인공 기본 이름', ko, tr_fix.DEFAULT_NAME[ja])); tr[i] = tr_fix.DEFAULT_NAME[ja]; continue
        if not ko.strip(): continue
        k2 = fix_brackets(ja, ko)
        if k2 != ko: changes.append((i, '괄호 되돌림', ko, k2)); ko = k2
        k3, why = tr_fix.fix(i, master[i][1][1], ja, ko)
        if k3 is None: changes.append((i, '넣지 않음: ' + why[0], ko, '')); skip.add(i); tr[i] = ''; continue
        if k3 != ko: changes.append((i, ' · '.join(why), ko, k3)); ko = k3
        if i in man and man[i] != ko: changes.append((i, '손 수정(data/tr_manual.tsv)', ko, man[i])); ko = man[i]
        tr[i] = ko
    rows = []; R = collections.defaultdict(list)
    for i in order:
        f, p = master[i]
        if i not in tr: continue
        if i in skip: continue
        if not tr[i].strip(): R['빈번역'].append((i, p[1], p[4], '')); continue
        rows.append(dict(id=i, file=p[1], pos=int(p[2], 16), n=int(p[3]), ja=p[4], ko=tr[i], tsv=f))
    C.init_vars(rows)
    _, keep = kfont.tables()
    for r in rows:
        i, f, ja, ko = r['id'], r['file'], r['ja'], r['ko']
        if B.tokens(ja) != B.tokens(ko) and i not in B.TOKEN_FREE_ID and ja != '誠{1FE}{FF00}': R['토큰'].append((i, f, ja, ko))
        plain = TOK.sub('', ko)
        if JP.search(''.join(c for c in plain if c not in tr_fix.KANJI_KEEP)): R['일본어남음'].append((i, f, ja, ko))
        miss = sorted({ch for ch in plain if not (kfont.is_ko(ch) or ch in keep or ch in C.HALF or ch == ' ')})
        if miss: R['글꼴없음'].append((i, f, ''.join(miss), ko))
        for m in JOSA.finditer(ko): R['변수조사'].append((i, f, m.group(0), ko))
    # 줄 넘침(빌더와 같은 순서: 부호 뒤 공백 → 자동 줄바꿈 → 검사)
    for r in rows:
        C.CUR[0] = (r['file'], r['pos'])
        r['ko2'] = C.reflow(r['file'], r['ja'], C.fit_fill(r['ja'], C.squeeze(r['ja'], r['ko'])))
        for pg, ln, w, lim, x in C.overflow(r['file'], r['ja'], r['ko2']):
            R['줄넘침'].append((r['id'], r['file'], '%s 쪽%d 줄%d 폭 %g>%g' % (C.kind(r['file'], r['ja']), pg, ln, w, lim), x))
    # 바이트·파일 크기(빌더 build_files 그대로, 글꼴 배정은 저장 안 함)
    km = kfont.assign({ch for r in rows for ch in r['ko2'] if kfont.is_ko(ch)}, save=False)
    for r in rows:
        if r['file'] == 'EVENT.BIN' or r['file'].endswith('.EVE') or r['file'] in B.INDEXED or r['file'] in B.FIXED_EVE: continue
        if r['file'] in B.EMBED_EVE and any(o <= r['pos'] < e for o, e, c in B.embedded(r['file'], open(os.path.join(B.D1, r['file']), 'rb').read())): continue
        if r['file'] in B.TABLE_MODS:
            bb = open(os.path.join(B.D1, r['file']), 'rb').read()
            if any(base <= r['pos'] < end for t, base, v, sent, end, refs in B.blocks(r['file'], bb)): continue
        try: nb = B.encode(r['ko2'], km, keep)
        except B.BuildError: continue
        # 정렬 패딩은 예산 아님(메모리 feedback_budget_is_original_length_not_padding, 2026-11-26)
        if len(nb) > r['n'] and B.direct_refs(r['file'], open(os.path.join(B.D1, r['file']), 'rb').read(), r['pos'], r['n'])[2]: continue
        if len(nb) > r['n']: R['바이트초과'].append((r['id'], r['file'], '%d > %d' % (len(nb), r['n']), r['ko2']))
    ok = [dict(r, ko=r['ko2']) for r in rows if not any(r['id'] == x[0] for k in ('토큰', '글꼴없음', '일본어남음') for x in R[k][:0])]
    bad_ids = {x[0] for k in ('토큰', '글꼴없음', '일본어남음') for x in R[k]}
    sim = [dict(r, ko=r['ko2']) for r in rows if r['id'] not in bad_ids and (r['file'] == 'EVENT.BIN' or r['file'].endswith('.EVE') or r['file'] in B.INDEXED or r['file'] in B.TABLE_MODS or r['file'] in B.FIXED_EVE or r['file'] in B.EMBED_EVE)]
    _, errs = B.build_files(sim, km, keep)
    for e in errs:
        if ('넘침' in e and '제자리' not in e) or '64 KB' in e or '경계' in e or '상한' in e: R['파일크기'].append(('', '', e, ''))
    # 화자 이름 표기
    sp = collections.defaultdict(collections.Counter)
    for r in rows:
        a, b = speaker(r['ja']), speaker(r['ko'])
        if a and b: sp[a][b] += 1
    for a, c in sorted(sp.items(), key=lambda x: -sum(x[1].values())):
        if len(c) > 1: R['화자표기'].append((a, '%d종' % len(c), ' / '.join('%s×%d' % kv for kv in c.most_common()), ''))
        top = c.most_common(1)[0][0]
        kana = a.strip()
        if kana and kana[0] in HK and top and top[0] != HK[kana[0]][0] and not top.startswith(HK[kana[0]]):
            R['음역'].append((a, top, '첫 글자 %s → %s 여야(거센소리 규칙)' % (kana[0], HK[kana[0]]), ''))
        if ('ツ' in kana or 'つ' in kana) and '쓰' in top: R['음역'].append((a, top, 'つ → 츠', ''))
    # 용어: A_01 표 번역
    gl = {}
    for r in rows:
        if r['file'] != 'A_01.BIN': continue
        jt = TOK.sub('', r['ja']).strip(); kt = TOK.sub('', r['ko']).strip()
        if '{FF01}' in r['ja'] or len(jt) < 3 or not kt or JP.search(kt) or not ('H001386' <= r['id'] <= 'H001804' or r['id'] < 'H001386'): continue
        if re.fullmatch(r'[ァ-ヺ・ー]+|[一-鿿]+', jt): gl.setdefault(jt, collections.Counter())[kt] += 1
    gl = {j: c.most_common(1)[0][0] for j, c in gl.items()}
    terms = sorted(gl, key=len, reverse=True); tc = collections.Counter(); te = {}
    for r in rows:
        if r['file'] == 'A_01.BIN': continue
        jt = TOK.sub('', r['ja']); used = set()
        for j in terms:
            if j in jt and not any(j in u for u in used):
                used.add(j)
                if gl[j] not in r['ko']: tc[j] += 1; te.setdefault(j, (r['id'], r['ko']))
    for j, n in tc.most_common(): R['용어'].append((j, gl[j], '%d줄' % n, '예 %s: %s' % te[j]))
    # 말투: 원문(일본어) 존댓말·반말과 번역 대조 — 문장 끝마다(보고만)
    JPOL = re.compile(r'(です|ます|ました|ません|でした|でしょう|ましょう|ございます|ください|下さい|ませ)[ぁ-ん]?[。!?！？…ー〜~、]*$')
    KPOL = re.compile(r'(요|니다|니까|세요|십시오|시오|소서)[.!?…~♪」』]*$')
    sp_mis = collections.defaultdict(lambda: [0, 0]); mis = []
    for r in rows:
        s_ja = [x for x in re.split(r'\{FF0[0-3]\}|[。!?！？]', re.sub(r'^\{FF19\}【[^】]*】\{FF16\}', '', r['ja'])) if TOK.sub('', x).strip()]
        s_ko = [x for x in re.split(r'\{FF0[0-3]\}|(?<=[.!?])', re.sub(r'^\{FF19\}【[^】]*】\{FF16\}', '', r['ko2'])) if TOK.sub('', x).strip()]
        if not s_ja or not s_ko: continue
        jp = sum(1 for x in s_ja if JPOL.search(TOK.sub('', x).strip())) / len(s_ja)
        kp = sum(1 for x in s_ko if KPOL.search(TOK.sub('', x).strip())) / len(s_ko)
        who = speaker(r['ko']) or speaker(r['ja']) or '(화자 없음)'
        sp_mis[who][1] += 1
        if (jp >= 0.5 and kp == 0) or (jp == 0 and kp >= 0.5):
            sp_mis[who][0] += 1; mis.append((r['id'], who, '원문 %s / 번역 %s' % ('존댓말' if jp >= 0.5 else '반말', '존댓말' if kp >= 0.5 else '반말'), r['ko']))
    for x in mis: R['말투'].append(x)
    with open(os.path.join(OUT, '말투_화자별.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('화자\t어긋난 줄\t전체 줄\n')
        for w, (a_, b_) in sorted(sp_mis.items(), key=lambda x: -x[1][0]):
            if a_: fh.write('%s\t%d\t%d\n' % (w, a_, b_))
    # 쓰기
    heads = {'변수조사': '조사', '화자표기': '표기들', '음역': '규칙', '용어': '줄 수', '말투': '화자\t원문/번역', '바이트초과': '바이트', '줄넘침': '자리'}
    for k in list(R) + ['형식']:
        L = R[k] if k != '형식' else bad
        with open(os.path.join(OUT, '%s.tsv' % k), 'w', encoding='utf-8') as fh:
            fh.write('id\t파일\t%s\t번역\n' % heads.get(k, '내용'))
            for x in L: fh.write('\t'.join(str(v) for v in x) + '\n')
    with open(os.path.join(OUT, 'changes.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('id\t사유\t전\t후\n'); [fh.write('\t'.join(c) + '\n') for c in changes]
    print('번역 받은 줄 %d (원문 %d) · 형식 문제 %d · 자동 수정 %d(괄호)' % (len(tr), len(master), len(bad), len(changes)))
    print('한글 음절 %d / 글꼴 칸 %d' % (len({ch for r in rows for ch in r['ko2'] if kfont.is_ko(ch)}), len(kfont.tables()[0])))
    for k in ('토큰', '글꼴없음', '일본어남음', '줄넘침', '바이트초과', '파일크기', '빈번역', '화자표기', '음역', '용어', '변수조사', '말투'):
        print('  %-6s %5d' % (k, len(R[k])))
    if '--merge' in sys.argv:
        dst = os.path.join(ROOT, 'data', 'tr'); os.makedirs(dst, exist_ok=True)
        if os.listdir(dst): shutil.copytree(dst, os.path.join(ROOT, 'work', 'tr_backup_' + time.strftime('%m%d_%H%M%S')))
        by = collections.defaultdict(list)
        for i in order: by[master[i][0]].append(i)
        for f, ids in by.items():
            with open(os.path.join(dst, f), 'w', encoding='utf-8') as fh:
                fh.write('id\t파일\t위치\t바이트\t원문\t번역\n')
                for i in ids: p = master[i][1]; fh.write('\t'.join(p[:5] + [tr.get(i, '')]) + '\n')
        print('병합 → data/tr (%d 파일)' % len(by))


if __name__ == '__main__':
    main()

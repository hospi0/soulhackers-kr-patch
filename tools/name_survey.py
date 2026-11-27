# -*- coding: utf-8 -*-
r"""고유명사 전수 검사(2026-11-27, 하스피 «전수검사 ㄱ» — 메모리 feedback_name_survey_bare_names: 진설 공개 철회 교훈)
  기준 표기 = 이 게임 데이터에서 뽑음
    ① 화자 이름표 【原】→【번역】 (가장 많이 쓴 표기)
    ② A_01 이름 표(아이템·악마·스킬·종족 = 한 줄짜리 이름 줄) 원문→번역
    ③ 지도·장소 이름(M00_2D·DGB_MAP 한 줄 이름)
  모든 번역 줄에서 «원문에 그 이름이 있는데 번역에 기준 표기가 없는» 줄을 보고(공백 무시 비교).
  python tools/name_survey.py → work/check/이름전수.tsv (이름별 묶음)"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
TOK = re.compile(r'\{[^}]*\}')
KATA = re.compile(r'^[ァ-ヶー・]+$')


def rows():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'tr', '*.tsv'))):
        for l in open(f, encoding='utf-8'):
            p = l.rstrip('\r\n').split('\t')
            if len(p) > 5 and p[0].startswith(('H', 'S')) and p[5]: out.append(p)
    return out


def plain(s): return TOK.sub('', s).replace('　', '').replace(' ', '')


def canon(R):
    """{원문 이름: (기준 번역, 근거)}"""
    D = {}; vote = collections.defaultdict(collections.Counter)
    for p in R:                                                         # ① 화자 이름표
        a = re.findall(r'【([^】]+)】', p[4]); b = re.findall(r'【([^】]+)】', p[5])
        if len(a) == len(b):
            for x, y in zip(a, b):
                if x not in ('???', '？？？') and y: vote[x][y] += 1
    for x, c in vote.items(): D[x] = (c.most_common(1)[0][0], '화자표')
    for p in R:                                                         # ② A_01 이름·③ 장소 이름(한 줄, 짧은 것)
        ja, ko = TOK.sub('', p[4]).strip('　 '), TOK.sub('', p[5]).strip('　 ')
        if '{FF01}' in p[4] or not ja or not ko or len(ja) > 12: continue
        if p[1] == 'A_01.BIN' or p[1] in ('M00_2D.BIN', 'DGB_MAP.BIN'):
            if re.search(r'[ァ-ヶ一-龥]', ja) and not re.search(r'[、。!?…「」]', ja) and (len(ja) >= 3 or (len(ja) >= 2 and not KATA.match(ja))):
                D.setdefault(ja, (ko, p[1]))
    return D


GENERIC = {'女', '声', '母', '男', '父', '子供', '人間', '女の子', '男の子', '少女', 'おばさん', 'メール', '条件', 'A', '悪魔', 'アナウンス', '若い男', '係員', 'パワー', 'イルカ', '西'}


_RX = {}


def found(nn, ja):
    """원문에 이름이 «낱말로» 있나 — 가타카나 이름은 앞뒤가 가타카나·ー 가 아니어야(インストール 의 トール 막기)
       (먼저 부분 문자열로 거르고, 정규식은 미리 한 번만 만듦 — 매번 만들면 캐시 밖이라 수 분 걸렸다)"""
    if nn not in ja: return False
    if not KATA.match(nn): return True
    rx = _RX.get(nn)
    if rx is None: rx = _RX[nn] = re.compile(r'(?<![ァ-ヶー])' + re.escape(nn) + r'(?![ァ-ヶー])')
    return rx.search(ja) is not None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = rows(); D = canon(R)
    for g in GENERIC: D.pop(g, None)
    for k in [k for k in D if re.search(r'[をにでと/]|体', k) or len(k) < 2]: D.pop(k)
    names = sorted(D, key=len, reverse=True)
    bad = collections.defaultdict(list)
    for p in R:
        ja, ko = plain(p[4]), plain(p[5])
        hit = set()
        for n in names:
            nn = n.replace('　', '').replace(' ', '')
            if found(nn, ja) and not any(nn in h for h in hit):
                hit.add(nn)
                k = D[n][0].replace(' ', '').replace('　', '')
                if k not in ko: bad[n].append(p)
    out = ['원문이름\t기준표기\t근거\t줄수\tid\t파일\t원문\t번역']
    tot = 0
    for n in sorted(bad, key=lambda n: -len(bad[n])):
        for p in bad[n]:
            out.append('%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s' % (n, D[n][0], D[n][1], len(bad[n]), p[0], p[1], p[4][:80], p[5][:80])); tot += 1
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'check', '이름전수.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('기준 이름 %d · 걸린 이름 %d · 줄 %d → work/check/이름전수.tsv' % (len(D), len(bad), tot))
    for n in sorted(bad, key=lambda n: -len(bad[n]))[:60]: print('  %-14s → %-12s %3d  (%s)' % (n, D[n][0], len(bad[n]), D[n][1]))


if __name__ == '__main__':
    main()

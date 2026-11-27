# -*- coding: utf-8 -*-
r"""시스템 글 1차 추출(2026-11-24) — 본편 EVENT.BIN·악마 대화 TALK*.EVE 빼고 모든 파일의 글 조각.
  조각 = scan_text.pieces(코드 2개 이상·빈 글리프 없음, 가나 없어도 됨) 전부.
  글다움(textscore) < −7.0(3자 이하) / −8.0(4자 이상) = «의심»(그림·표 바이트가 글처럼 보이는 것 — 짧은 진짜 낱말도 섞임)
  그림·소리 데이터 파일(SKIP)은 표본 눈 확인으로 뺌
  ⚠️경계는 «코드 2바이트 연속 조각» 기준 — 포인터·표 소비자 확인 전(재삽입 전 반드시 표 구조로 다시 끊을 것)
  출력 data/sys_ja.tsv : id · 파일 · 위치(16진) · 바이트 · 점수 · 판정 · 원문(글꼴 표로 풀이)
  python tools/extract_sys.py"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import scan_text, textscore, charmap
D1 = os.path.join(ROOT, 'work', 'disc1')
SKIP = ('EVENT.BIN', 'EVE_MES.BIN', 'MESS.BIN',          # 본편·그림
        'DGO_BMP.BIN', 'DEVILCG.BIN', 'Z_BG.BIN', 'KEN.TXB', 'GOUMA.CHR', 'SWDIMG.BIN', 'TC_CP.BIN', 'Z_CPK.BIN',
        'DGQ_MES.BIN', 'DGA_CBG.BIN', 'Z_KEY.SPR', 'DS2SOUND.BIN', 'DVL_BAT2.BIN', 'DVL_BAT3.BIN', 'MIX.DAT',
        'I_BOUGU.CPK', 'I_MAG.CPK', 'GO_EF0.CPK', 'KENCPK.BIN', 'TC_CPK.BIN', 'TC_CPKE.BIN')   # 그림·소리 데이터(표본 눈 확인 2026-11-24)


def dec(codes, m):
    return ''.join(m[c][0] if c in m and m[c][0] else '{%03X}' % c for c in codes)


def main():
    sys.stdout.reconfigure(encoding='utf-8'); sc = textscore.model(); m = charmap.load()
    out = ['id\t파일\t위치\t바이트\t점수\t판정\t원문']; per = {}; sus_n = 0
    for f in sorted(glob.glob(os.path.join(D1, '*'))):
        b = os.path.basename(f)
        if b in SKIP or b.startswith('TALK') or f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        d = open(f, 'rb').read(); n = 0
        for st, c in scan_text.pieces(d, kana=False):
            s = sc(c); sus = s < (-7.0 if len(c) <= 3 else -8.0)
            out.append('S%05d\t%s\t%X\t%d\t%.1f\t%s\t%s' % (len(out), b, st, 2 * len(c), s, '의심' if sus else '', dec(c, m)))
            if sus: sus_n += 1
            else: n += len(c)
        if n: per[b] = n
    open(os.path.join(ROOT, 'data', 'sys_ja.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    for b, n in per.items(): print('%-14s %7d자' % (b, n))
    print('합 %d줄(의심 %d) · 의심 뺀 %d자' % (len(out) - 1, sus_n, sum(per.values())))


if __name__ == '__main__':
    main()

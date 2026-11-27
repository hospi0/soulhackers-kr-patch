# -*- coding: utf-8 -*-
r"""한 글자 메시지 보충 추출(2026-11-25) — extract_all 은 글자 2개 미만 메시지를 버려서 「回」(FF99 횟수 접미어)·
  力知魔耐速運·左右·頭胴腕足·春夏秋冬 같은 한 글자 선택지·표 항목 123개가 빠졌다.
  규칙: [글 코드 1개]{FF00} 이고 바로 앞이 {FF00}(앞 메시지 끝) 또는 00 00(정렬 패딩).
  ⛔번역 중인 sh_001~174 의 id 를 안 바꾸려고 따로 S 번호로 → work/tsv/sh_175.tsv + data/sh_ja.tsv 끝에 덧붙임(이미 있으면 안 덧붙임)
  python tools/extract_single.py"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import charmap, extract_all as X


def main():
    sys.stdout.reconfigure(encoding='utf-8'); m = charmap.load(); rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'disc1', '*'))):
        bn = os.path.basename(f)
        if bn in X.SKIP or f.endswith(('.AVI', '.AIF')) or os.path.getsize(f) > 30_000_000: continue
        d = open(f, 'rb').read()
        for mm in re.finditer(rb'(?<=\xff\x00|\x00\x00)[\xc0-\xdf][\x80-\xbf]\xff\x00', d):
            i = mm.start()
            if d[i - 2:i] == b'\xff\x00' or (d[i - 2:i] == b'\x00\x00'):
                k = ((d[i] & 0x1F) << 6) | (d[i + 1] & 0x3F); ch = m.get(k, ('', ''))[0] or '{%03X}' % k
                rows.append((bn, i, ch + '{FF00}'))
    out = ['id\t파일\t위치\t바이트\t원문\t번역'] + ['S%05d\t%s\t%X\t4\t%s\t' % (n + 1, f, i, t) for n, (f, i, t) in enumerate(rows)]
    open(os.path.join(ROOT, 'work', 'tsv', 'sh_175.tsv'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    p = os.path.join(ROOT, 'data', 'sh_ja.tsv'); s = open(p, encoding='utf-8').read()
    if '\nS00001\t' not in s:
        s = s.rstrip('\n') + '\n' + '\n'.join('S%05d\t%s\t%X\t4\t\t%s' % (n + 1, f, i, t) for n, (f, i, t) in enumerate(rows)) + '\n'
        open(p, 'w', encoding='utf-8').write(s)
    print('한 글자 메시지 %d줄 → work/tsv/sh_175.tsv' % len(rows))


if __name__ == '__main__':
    main()

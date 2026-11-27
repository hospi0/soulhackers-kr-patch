# -*- coding: utf-8 -*-
r"""소울 해커즈 전체 대사·메시지 추출(2026-11-25, 하스피 «모든 대사 메시지 뽑아서 tsv»)
  글 코드 = 2바이트 110xxxxx 10xxxxxx(11비트 = 글꼴 칸), 1바이트 0x20 = 반각 공백(원문에 « »), 제어 = 0xFF xx(xx 무관, FF81·FF93 = 이름 변수로 보임) → {FFxx} 토큰으로 원문에 그대로.
  한 줄(메시지) = 글 코드·제어 코드가 끊김 없이 이어진 덩어리를 {FF00}(메시지·선택지 항목 끝)에서 끊은 것, 글 코드 2개 이상.
  대상 = work/disc1 의 모든 파일 − 그림·소리 데이터(extract_sys.SKIP, EVENT·TALK 는 포함).
  판정: textscore 글다움 < −7.0(3자 이하)/−8.0(4자 이상) = «의심»(그림·표 바이트가 글처럼 보이는 것). 단 {FF00} 으로 끝나는 줄은 진짜(의심 아님).
  ⚠경계는 바이트 덩어리 기준 — 스크립트 명령·포인터 구조 확인 전(재삽입 전에 다시 볼 것). 한자 판독표 data/charmap.tsv 오독 칸 있음.
  출력: data/sh_ja.tsv(전부, 판정 열) · work/tsv/sh_NNN.tsv(의심 뺀 번역용, 18 KB 단위 — 열: id·파일·위치·바이트·원문·번역)
  python tools/extract_all.py"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import charmap, textscore, extract_sys
D1 = os.path.join(ROOT, 'work', 'disc1')
SKIP = set(extract_sys.SKIP) - {'EVENT.BIN'}
SPLIT = 18 * 1024


def messages(d):
    """[(시작, 끝, [('t', 칸) | ('c', 제어)])]"""
    out = []; cur = []; st = 0; i = 0; n = len(d)
    def flush():
        if sum(1 for k, _ in cur if k == 't') >= 2: out.append((st, i, list(cur)))
        elif cur and out and out[-1][1] == st and all(k == 'c' for k, _ in cur): pass
    while i < n - 1:
        b, c = d[i], d[i + 1]
        if 0xC0 <= b < 0xE0 and 0x80 <= c < 0xC0:
            if not cur: st = i
            cur.append(('t', ((b & 0x1F) << 6) | (c & 0x3F))); i += 2; continue
        if b == 0x20:                              # 1바이트 반각 공백도 메시지 안에 섞임(«ITEM USE»·«北が上  正面が上», 2026-11-25)
            if not cur: st = i
            cur.append(('s', 0x20)); i += 1; continue
        if b == 0xFF:                              # 0xFF 는 글 코드 첫 바이트가 아님 → xx 상관없이 제어(FF81·FF93 = 이름 변수로 보임)
            if not cur: st = i
            cur.append(('c', c)); i += 2
            if c == 0x00:                          # {FF00} = 메시지 끝(선택지 항목 끝도) → 여기서 끊음
                flush(); cur = []
            continue
        flush(); cur = []; i += 1
    flush()
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8'); m = charmap.load(); sc = textscore.model()
    rows = ['id\t파일\t위치\t바이트\t판정\t원문']; good = []; per = {}
    files = [f for f in sorted(glob.glob(os.path.join(D1, '*'))) if os.path.basename(f) not in SKIP and not f.endswith(('.AVI', '.AIF'))
             and os.path.getsize(f) <= 30_000_000]
    for f in files:
        b = os.path.basename(f); d = open(f, 'rb').read(); n = 0
        for st, en, toks in messages(d):
            codes = [v for k, v in toks if k == 't']
            s = sc(codes); sus = s < (-7.0 if len(codes) <= 3 else -8.0)
            if toks[-1] == ('c', 0x00): sus = False          # {FF00}(메시지 끝)으로 끝나면 진짜 — 짧은 이름·낱말(基本防御·邪鬼·傷薬)이 의심으로 빠지던 것(2026-11-25 점검)
            txt = ''.join((m[v][0] if v in m and m[v][0] else '{%03X}' % v) if k == 't' else ' ' if k == 's' else '{FF%02X}' % v for k, v in toks)
            # 맨 끝 제어 코드는 덩어리 끝 표시라 원문에 두되 바이트는 마지막 제어까지
            rid = 'H%06d' % len(rows)
            rows.append('%s\t%s\t%X\t%d\t%s\t%s' % (rid, b, st, en - st, '의심' if sus else '', txt))
            if not sus:
                good.append('%s\t%s\t%X\t%d\t%s\t' % (rid, b, st, en - st, txt)); n += len(codes)
        if n: per[b] = n
    open(os.path.join(ROOT, 'data', 'sh_ja.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(rows) + '\n')
    outd = os.path.join(ROOT, 'work', 'tsv'); os.makedirs(outd, exist_ok=True)
    for f in glob.glob(os.path.join(outd, 'sh_*.tsv')): os.remove(f)
    head = 'id\t파일\t위치\t바이트\t원문\t번역'; k = 0; buf = [head]; size = len(head.encode()) + 1
    for l in good:
        ln = len(l.encode()) + 1
        if size + ln > SPLIT and len(buf) > 1:
            k += 1; open(os.path.join(outd, 'sh_%03d.tsv' % k), 'w', encoding='utf-8', newline='\n').write('\n'.join(buf) + '\n')
            buf = [head]; size = len(head.encode()) + 1
        buf.append(l); size += ln
    if len(buf) > 1:
        k += 1; open(os.path.join(outd, 'sh_%03d.tsv' % k), 'w', encoding='utf-8', newline='\n').write('\n'.join(buf) + '\n')
    for b, n in sorted(per.items(), key=lambda x: -x[1]): print('%-14s %7d자' % (b, n))
    print('전체 %d줄 · 번역용 %d줄 %d자 · work/tsv/sh_001~%03d.tsv' % (len(rows) - 1, len(good), sum(per.values()), k))


if __name__ == '__main__':
    main()

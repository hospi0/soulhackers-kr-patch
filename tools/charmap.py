# -*- coding: utf-8 -*-
"""글꼴 칸 → 문자 최종 표 data/charmap.tsv (칸 16진 · 문자 · 근거)
근거: 고정(ASCII·히라·가타, ocrmap.fixed) > 손(MANUAL) > OCR 다수결(3표+60%, work/ocr/vote.tsv) > OCR 약함 > 모양 대조(work/charmap.tsv)
python tools/charmap.py → 표 쓰고, 글 파일들에서 쓰인 칸 중 근거 약한 칸 수 출력"""
import collections, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import ocrmap
MANUAL = {0x1F5: '。', 0x1F6: '、', 0x1F7: '【', 0x1F8: '】', 0x257: 'ー', 0x140: '　',
          # 2026-11-25 교정 시트(tools/charfix.py) 눈 확인 — OCR 이 문맥으로 틀리게 읽은 칸
          0x264: '威', 0x2CA: '一', 0x33A: '鏡', 0x35F: '絵', 0x388: '臭', 0x417: '細', 0x470: '齢', 0x4D4: '消', 0x4F3: '繰',
          0x500: '格', 0x507: '令', 0x51F: '僧', 0x56B: '慢', 0x5F4: '憎', 0x5FE: '漂', 0x61D: '…', 0x68E: '○', 0x6BF: '妹',
          0x6C4: '娘', 0x6E3: '診', 0x6E6: '担', 0x6FE: '慣', 0x70E: '×', 0x710: '姉', 0x717: '汁', 0x744: '模', 0x787: '麗',
          0x413: '断', 0x555: '決',   # OCR 이 번체·간체로 읽음
          0x654: '撤',                # 낱자 재판독(tools/kanji_recheck.py) 눈 확인
          0x1EE: '　'}               # 히라가나 순서상 «ゎ» 자리지만 글리프가 비어 있음 = 공백으로 씀(«ゎゎゎが高いぜっ»)


def load():
    m = {}
    for l in open(os.path.join(ROOT, 'data', 'charmap.tsv'), encoding='utf-8').read().splitlines()[1:]:
        k, ch, why = l.split('\t'); m[int(k, 16)] = (ch, why)
    return m


def build():
    FX = ocrmap.fixed(); m = {}
    for l in open(os.path.join(ROOT, 'work', 'charmap.tsv'), encoding='utf-8').read().splitlines()[1:]:
        f = l.split('\t')
        if f[1]: m[int(f[0], 16)] = (f[1], '모양%s' % f[2])
    for l in open(os.path.join(ROOT, 'work', 'ocr', 'vote.tsv'), encoding='utf-8').read().splitlines()[1:]:
        k, ch, v, t = l.split('\t')[:4]; k = int(k, 16); v, t = int(v), int(t)
        m[k] = (ch, 'OCR%d/%d' % (v, t) if v >= 3 and v / t >= 0.6 else 'OCR약%d/%d' % (v, t))
    for k, ch in FX.items(): m[k] = (ch, '고정')
    for k, ch in MANUAL.items(): m[k] = (ch, '손')
    with open(os.path.join(ROOT, 'data', 'charmap.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('칸\t문자\t근거\n')
        for k in sorted(m): f.write('%03X\t%s\t%s\n' % (k, m[k][0], m[k][1]))
    return m


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import scan_text
    m = build(); use = collections.Counter()
    for f in glob.glob(os.path.join(ROOT, 'work', 'disc1', '*')):
        b = os.path.basename(f)
        if b.startswith(('EVENT', 'TALK', 'I_SHOP', 'GOMADEN.EVE', 'A_01')):
            for _, c in scan_text.pieces(open(f, 'rb').read()): use.update(c)
    weak = [(k, n) for k, n in use.items() if k not in m or not m[k][1].startswith(('고정', '손', 'OCR'))]
    weak2 = [(k, n) for k, n in use.items() if k in m and m[k][1].startswith('OCR약')]
    print('쓰인 칸 %d · 표 없음/모양만 %d칸(%d회) · OCR 약함 %d칸(%d회)' % (len(use), len(weak), sum(n for _, n in weak), len(weak2), sum(n for _, n in weak2)))

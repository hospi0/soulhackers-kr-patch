# -*- coding: utf-8 -*-
r"""코드 모듈 속 문자열 위치표 찾기(2026-11-26, 하스피 «바이트초과부터 쭉 잡자»)
  구조(DGC_CMP 0x30198 에서 확인): u16 위치표 n칸(첫 칸 0, 늘어나는 값) 바로 뒤가 기준(base), 문자열 = base + 표값.
  코드는 표 주소와 기준 주소를 리터럴로 들고 있음(예 DGC_CMP 0xE188 = 표, 0xE190 = 기준).
  찾는 법: 모듈 안 u32 값 중 «적재 주소 + 파일 안 위치» 인 것 → 그 위치에서 u16 표(0 시작·증가)가 이어지고 표 끝 = 다른 리터럴(기준) 이면 표.
  python tools/strtab.py DGC_CMP.BIN 0x06030000"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
D1 = os.path.join(ROOT, 'work', 'disc1')


def literals(d, B):
    """{파일 안 위치: [리터럴 자리…]} — 4바이트 정렬 u32 중 B..B+len"""
    out = {}
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack_from('>I', d, i)[0]
        if B <= v < B + len(d): out.setdefault(v - B, []).append(i)
    return out


def tables(d, B):
    """[(표 위치, 기준, 칸 수, [기준 리터럴 자리])]"""
    lit = literals(d, B); res = []
    for t in sorted(lit):
        if t % 2 or struct.unpack_from('>H', d, t)[0] != 0: continue
        for base in sorted(x for x in lit if t < x <= t + 0x2000 and (x - t) % 2 == 0):
            n = (base - t) // 2
            if n < 2: continue
            v = struct.unpack_from('>%dH' % n, d, t)
            if len(v) >= 2 and v[-1] == 0 and v[-2] == 0xFFFF: v = v[:-1]   # FFFF 뒤 0000 채움(DGB_MAP 0x2543E)
            if v[-1] == 0xFFFF: v = v[:-1]                                   # 끝 표시(DGC_CMP 0x30198 표 마지막 칸 FFFF)
            if len(v) < 2: continue
            if all(a < b for a, b in zip(v, v[1:])) and base + v[-1] < len(d) and all(d[base + x - 2:base + x] in (b'\xff\x00', b'\x00\x00') or x == 0 for x in v):
                res.append((t, base, n, lit[base])); break
    return res


def block_end(d, base, v):
    """마지막 문자열 끝({FF00} 다음)"""
    i = base + v[-1]
    while i + 1 < len(d) and d[i:i + 2] != b'\xff\x00': i += 2 if d[i] >= 0xC0 or d[i] == 0xFF else 1
    return i + 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    f, B = sys.argv[1], int(sys.argv[2], 16); d = open(os.path.join(D1, f), 'rb').read()
    for t, base, n, refs in tables(d, B):
        v = struct.unpack_from('>%dH' % n, d, t)
        if v[-1] == 0xFFFF: v = v[:-1]
        print('표 %X 기준 %X 칸 %d 끝 %X · 기준 리터럴 %s' % (t, base, n, block_end(d, base, v), [hex(r) for r in refs]))

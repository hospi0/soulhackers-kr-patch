# -*- coding: utf-8 -*-
r"""전투 파티 칸 이름 한글(2026-11-27, 하스피 «전투창 글자 깨짐»·«전투 ㄱ»)
  원래: DVL_BAT1 0x0604201E 이름 루프 → 글자 코드(u16)를 0x06041E44 로 변환(전각 글꼴 번호 − 0x120) →
        대사 글꼴 RAM 0x0020000C + 번호×32 (= 그 칸 6~15줄) 의 왼쪽 8열을 찍음 = 반각 칸 왼쪽 반의 «작은 가나».
        한글은 가나 칸 번호를 빌려 써서 작은 가나(베스 → めイ)가 나옴.
  훅: 변환 함수 자리(리터럴 0x06042188 하나 — 부르는 곳 0x06042026 뿐)를 HOOK 으로.
        전각 번호 ≥ 0x1A1(한글) → 그 16×16 글자를 2:1(2×2 중 하나라도 켜짐)로 줄여 임시 칸 TMP 의 6~15줄 왼쪽 반에 그림
        (6줄 0, 7~14줄 = 8줄, 15줄 0) → TMP 돌려줌.  그 밖 → 원래 계산(번호 − 0x120).
  레지스터: 원래 함수는 R0·R1·R2(+R14 저장)만 씀 → 훅도 R0~R2 밖(R3·R5·R6·R7)은 스택 보존.
  자리: A_01 뒤 RAM 0x21FE00(A_01 = RAM 0x210000~, 0x21B6F6~0x220000 빈 곳 — 스테이트 8장 0·코드 리터럴 없음, 전투 중 상주)."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sh2asm

HOOK = 0x0021FE00
A01_RAM = 0x00210000
LIT = 0x12188; ORIG = 0x06041E44                                       # DVL_BAT1 파일 자리(RAM 0x06042188)


def code(tmp):
    dst = 0x00200000 + tmp * 32 + 12
    src = f"""
    mov.l r3,@-r15
    mov.l r5,@-r15
    mov.l r6,@-r15
    mov.l r7,@-r15
    extu.w r4,r0
    mov.l #0x3F00,r1
    and r0,r1
    shlr2 r1
    mov #0x3F,r2
    and r2,r0
    add r1,r0
    mov.l #0x1A1,r1
    cmp/hs r1,r0
    bt big
    mov.l #0xFFFFFEE0,r1
    bra done
    add r1,r0
big:
    shll2 r0
    shll2 r0
    shll r0
    mov.l #0x200000,r1
    add r1,r0
    mov.l #{dst},r5
    mov #0,r1
    mov.w r1,@r5
    add #2,r5
    mov #8,r6
    mov.l #0xC000,r3
row:
    mov.w @r0+,r1
    mov.w @r0+,r2
    or r2,r1
    extu.w r1,r1
    mov #0,r2
    mov #8,r7
col:
    shll r2
    tst r3,r1
    bt skip
    add #1,r2
skip:
    shll2 r1
    dt r7
    bf col
    shll8 r2
    mov.w r2,@r5
    add #2,r5
    dt r6
    bf row
    mov #0,r1
    mov.w r1,@r5
    mov.l #{tmp},r0
done:
    mov.l @r15+,r7
    mov.l @r15+,r6
    mov.l @r15+,r5
    rts
    mov.l @r15+,r3
"""
    return sh2asm.assemble(src, HOOK)


def patch(a01, dvl, tmp):
    """(A_01 바이트, DVL_BAT1 바이트, 임시 칸) → 둘 다 고친 것"""
    c = code(tmp); off = HOOK - A01_RAM
    a = bytearray(a01); assert len(a) <= off, ('A_01 이 훅 자리를 침범', hex(len(a)), hex(off))
    a += bytes(off - len(a)) + c; assert len(a) <= 0x10000
    d = bytearray(dvl); assert struct.unpack('>I', d[LIT:LIT + 4])[0] == ORIG, '변환 함수 리터럴이 원본과 다름'
    struct.pack_into('>I', d, LIT, HOOK)
    return bytes(a), bytes(d)


def simulate(font, code_u16, tmp):
    """훅이 TMP 칸에 그릴 10줄(왼쪽 8비트)을 파이썬으로 — 검산·미리보기용"""
    full = ((code_u16 & 0x3F00) >> 2) + (code_u16 & 0x3F)
    if full < 0x1A1: return full - 0x120, None
    rows = [struct.unpack('>H', font[full * 32 + k * 2:full * 32 + k * 2 + 2])[0] for k in range(16)]
    out = [0]
    for r in range(8):
        w = rows[2 * r] | rows[2 * r + 1]; o = 0
        for j in range(8): o = (o << 1) | (1 if w & (0xC000 >> (2 * j)) else 0)
        out.append(o << 8)
    return tmp, out + [0]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    c = code(0x7A6)
    print(len(c), 'B'); import sh2dis
    print('\n'.join(sh2dis.dis(c, HOOK, HOOK, len(c) // 2)))

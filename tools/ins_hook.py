# -*- coding: utf-8 -*-
r"""회복 장소·설치(INS.BIN) 반각 글자 한글(2026-11-27, 하스피 «파티이름 여기서만 깨짐·메뉴도 깨짐 → 훅 ㄱ»)
  원래: INS 글 그리기 두 곳(0x0603E5xx·0x0603E8xx)의 «앞바이트 0xE?/0xF?» 반각 경로가
        코드 = ((앞&0xF)<<6 | 뒤&0x7F) − 0x120 을 그리기 함수 0x0603D658 에 넘김.
        그리기 함수는 번호 ≤ 0x13F 면 반각: 글꼴 RAM 0x200000 + 번호×32 의 0~14줄, 한쪽 8열(플래그 0x06073660 → 0x0080/0x8000 마스크)을 찍음.
        한글(전각 번호 ≥ 0x1A1)은 번호 −0x120 칸(엉뚱한 칸)의 반쪽이 찍혀 가나처럼 깨짐(네미사 → けぽら, 스테이터스 → ィミザマィ).
        (스테이트 work/states/heal_1127.state1 — 이름 글자 = 글꼴 칸 0x91·0xBC·0xC9 오른쪽 반 = 0x1B1·0x1DC·0x1E9 − 0x120 로 확인)
  훅: 두 경로가 그리기 함수를 부르는 리터럴(0x0603E73C·0x0603E9F4 — 같은 함수의 전각 경로도 이 리터럴을 씀)을 HOOK 으로.
        PR(돌아갈 자리)이 반각 경로(0x0603E70C·0x0603E946)이고 번호+0x120 ≥ 0x1A1 이면
        그 16×16 한글을 가로 2:1(두 열 중 하나라도 켜짐)로 줄여 임시 칸 TMP(0x13F, 원래 빈 칸)의 0~14줄 «양쪽 반 모두»에 그리고 번호 = TMP.
        그 밖은 그대로 원래 함수로 점프(JMP — 돌아갈 자리 PR 그대로).
  레지스터: 원래 함수 입력 R4·R5·R7 그대로, R6 만 바꿈. 훅이 쓰는 R0~R3 은 원래 함수도 덮어씀(호출자가 기대 안 함), R8~R10 은 스택 보존.
  자리: A_01 뒤 RAM 0x21FF00(전투 HUD 훅 0x21FE00~ 다음 — 받은 스테이트 전부 0x21FE90~0x21FFFF 0, INS 화면에서도 A_01 상주 확인)."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sh2asm

HOOK = 0x0021FF00
A01_RAM = 0x00210000
ORIG = 0x0603D658
LITS = (0xE73C, 0xE9F4)                                                # INS 파일 자리(RAM 0x0603E73C·0x0603E9F4)
RET_HALF = (0x0603E70C, 0x0603E946)
TMP = 0x13F


def code():
    dst = 0x00200000 + TMP * 32
    src = f"""
    mov.l r8,@-r15
    mov.l r9,@-r15
    mov.l r10,@-r15
    sts.l pr,@-r15
    mov.l @r15+,r0
    mov.l #{RET_HALF[0]},r1
    cmp/eq r1,r0
    bt half
    mov.l #{RET_HALF[1]},r1
    cmp/eq r1,r0
    bf orig
half:
    extu.w r6,r0
    mov.l #0x120,r1
    add r1,r0
    mov.l #0x1A1,r1
    cmp/hs r1,r0
    bf orig
    shll2 r0
    shll2 r0
    shll r0
    mov.l #0x200000,r1
    add r1,r0
    mov.l #{dst},r8
    mov #15,r9
    mov.l #0xC000,r10
row:
    mov.w @r0+,r1
    extu.w r1,r1
    mov #0,r2
    mov #8,r3
col:
    shll r2
    tst r10,r1
    bt skip
    add #1,r2
skip:
    shll2 r1
    dt r3
    bf col
    mov r2,r1
    shll8 r1
    or r1,r2
    mov.w r2,@r8
    add #2,r8
    dt r9
    bf row
    mov #0,r1
    mov.w r1,@r8
    mov.l #{TMP},r6
orig:
    mov.l @r15+,r10
    mov.l @r15+,r9
    mov.l @r15+,r8
    mov.l #{ORIG},r0
    jmp @r0
    nop
"""
    return sh2asm.assemble(src, HOOK)


def patch(a01, ins):
    """(A_01 바이트 — 전투 HUD 훅까지 붙은 것, INS 바이트) → 둘 다 고친 것"""
    c = code(); off = HOOK - A01_RAM
    a = bytearray(a01); assert len(a) <= off, ('A_01 이 INS 훅 자리를 침범', hex(len(a)), hex(off))
    a += bytes(off - len(a)) + c; assert len(a) <= 0x10000
    d = bytearray(ins)
    for lit in LITS:
        assert struct.unpack('>I', d[lit:lit + 4])[0] == ORIG, ('그리기 함수 리터럴이 원본과 다름', hex(lit))
        struct.pack_into('>I', d, lit, HOOK)
    return bytes(a), bytes(d)


def simulate(font, full):
    """훅이 TMP 칸에 그릴 16줄(u16) — 검산·미리보기용"""
    rows = [struct.unpack('>H', font[full * 32 + k * 2:full * 32 + k * 2 + 2])[0] for k in range(15)]
    out = []
    for w in rows:
        o = 0
        for j in range(8): o = (o << 1) | (1 if w & (0xC000 >> (2 * j)) else 0)
        out.append((o << 8) | o)
    return out + [0]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    c = code(); print(len(c), 'B'); import sh2dis
    print('\n'.join(sh2dis.dis(c, HOOK, HOOK, len(c) // 2)))

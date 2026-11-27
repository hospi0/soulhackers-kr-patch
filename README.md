# 데빌 서머너 소울 해커즈 (세가 새턴 일본판 2장) 한글 패치

시험 단계(v0.9) 한글 패치입니다. 배포 묶음(xdelta)은 릴리즈에 있습니다.

- 적용 대상: Devil Summoner - Soul Hackers (Japan) Disc 01·02 의 트랙 1
- 원본 md5: 디스크 1 `3D18516108C408D936AE729B7A4047CA` · 디스크 2 `0628BA7614F97E0BFDA1FC7A2238B2C7`

## 폴더

- `tools/` — 추출·빌드·훅·배포 스크립트 (`build.py` 빌더, `make_dist.py` 배포 묶음)
- `data/tr/` — 번역(id·파일·위치·바이트·원문·번역), `data/tr_manual.tsv` 손 수정
- `data/charmap.tsv`·`data/kmap.json` — 글꼴 칸 판독표·한글 칸 배정
- `docs/` — 조사·작업 기록

원본 게임 데이터(ROM·그림·음성)는 들어 있지 않습니다.

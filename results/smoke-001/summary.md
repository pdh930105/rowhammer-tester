# Rowhammer smoke test 결과 — smoke-001 (2026-09-16 22:15)

## 실험 조건
| 항목 | 값 |
| --- | --- |
| 보드 | Xilinx ZCU104 (`xczu7ev-ffvc1156-2-i`) |
| 게이트웨어 | 125 MHz SPD 빌드, bitstream sha256 `702d158f83db36eb4b5897855d6d1c98928e019629f9f9d876babbad200b0f97` |
| ident | `git: 2ab8a67fa2f2c588fdb05145d5d1a7ddbde4a412 2026-09-16 17:29:22` |
| SO-DIMM | Samsung `M471A5244CB0-CTD` (4 GB, 1Rx16, 8 Gbit x16, DDR4-2666) |
| SPD | `build/zcu104/spd.bin`, sha256 `791927d0908932e193d8ce95e9aaed67f5b86222676161e905bb81f6cfdb41eb` |
| 제어 | UARTBone `/dev/ttyUSB4` @1 Mbaud |
| 필수 전제 | FTDI `latency_timer=1` (16 ms → 1 ms), BIOS 콘솔 드레인으로 `ddrctrl_init_done=1` 달성 |

## 실행
```sh
TARGET=zcu104 venv/bin/python rowhammer_tester/scripts/hw_rowhammer.py \
  --pattern 01_in_row --all-rows --start-row 3 --nrows 8 \
  --read_count 10000 --log-dir results/smoke-001
```
- refresh **ON** (기본), `--no-refresh` 미사용
- 패턴: `01_in_row` (0xAAAAAAAA)

## 결과 — **PASS**
- `Filling memory with data` → 16777216/16777216 OK
- `Verifying written memory` → **Errors: 0** (`OK`)
- `Running Rowhammer attacks` → `read_count: 10000`, 3개 row pair: (3,5), (4,6), (5,7)
- `Verifying attacked memory` → **Errors: 0** (`OK`)
- `results/smoke-001/error_summary_*.json`:
  ```json
  {"10000": {"read_count": 10000,
     "pair_3_5": {"hammer_row_1": 3, "hammer_row_2": 5, "errors_in_rows": {}},
     "pair_4_6": {"hammer_row_1": 4, "hammer_row_2": 6, "errors_in_rows": {}},
     "pair_5_7": {"hammer_row_1": 5, "hammer_row_2": 7, "errors_in_rows": {}}}}
  ```
  → 모든 pair에서 `errors_in_rows`가 빈 딕셔너리 = **bit flip 0건** (read_count 1e4의 소규모 test에서는 정상)

## 판정
- 게이트 E의 첫 단계(소규모 smoke test + 결과 로그 생성) **성공**
- DRAM 읽기/쓰기/BIST/공격 파이프라인 전체가 정상 동작함을 확인

## 다음 단계 (점진 확대)
1. `--read_count` 1e4 → 1e5 → 1e6
2. row 범위 확대 (`--nrows`, `--row-jump`)
3. 정상 재현이 확인된 뒤에만 `--no-refresh` 사용 (데이터 손상 유발 가능, 주의)
4. 각 실험마다 bit flip 수, 주소, 실행 시간, SPD/bitstream hash, git commit 기록

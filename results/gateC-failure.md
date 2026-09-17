# Gate C 실패 기록 — ZCU104 DDR4 BIST 검증 (2026-09-16)

## 결론
**게이트 C 미통과.** BIST 메모리 테스트에서 데이터 오류가 발생했고, 근본 원인은
**LiteX BIOS의 DRAM 초기화/트레이닝이 완료되지 않는 것**(`ddrctrl_init_done`이 계속 0)으로 보인다.
게이트 D(microSD 영구 반영)는 진행하지 않음.

## 통과한 게이트
- Gate A: 빌드/타이밍/DRC 통과, bitstream SHA-256 = 702d158f...0b0f97 (results/manifest.txt 참고)
- Gate B: JTAG 프로그래밍 성공 (`End of startup status: HIGH`)
- UARTBone 통신 OK: `version.py` → `xczu7ev-ffvc1156-2-i, git: 2ab8a67fa2f...`

## 실패 증상 (실행별)
| run | 조건 | 결과 |
| --- | --- | --- |
| run1 | 최초 프로그래밍 직후 | 패턴 `0xFFFFFFFF`에서 1961건 오류 → 이후 reader 멈춤 |
| run2 | run1 직후(리셋 없음) | 1 GiB write 완료 후 reader가 `ready=0`이라 즉시 assert |
| run4 | 재프로그래밍 직후 | 시작부터 오류 폭증하며 진행 정지(~2900/16777216), reader stall |
| mem.py | 90s / 300s 대기 | DRAM 초기화 미완료(`Initialization succeeded` 미출력, timeout) |

## run1 오류 분포 (핵심)
- 총 1961건, 전부 **고유 주소**, 64B(0x40) 스텝으로 **연속**.
- 두 구간에만 몰림:
  - `0x40000000`(main_ram base) 부터 약 **34 KB**
  - `0x49B7F440`(≈155.6 MiB) 부터 약 **88 KB**
- **1961건 모두 동일한 손상 값**:
  `0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000000000000000000000000000ffffffffffffffffffffffffffffffff`
  → 64B 비트 중 **한 DFI phase(16B=128bit)가 0**으로 읽힘. 기대값은 전부 0xff.
- 값이 주소마다 동일하다는 점은 개별 셀 결함보다는 **DFI phase/PHY 경로의 체계적 문제** 가능성을 시사.

## 레지스터 근거
- `ddrctrl_init_done = 0` (재프로그래밍 후 300s+ 경과에도 0)
- `ddrctrl_init_error = 0`
- BIOS 출력(uart_xover): read leveling `m0..m7 ... delay: 372/373` 이후 **write leveling 단계로 보이는 곳에서 정지**
- `main_ram = 0x40000000, size = 1 GiB` (csr.csv). DIMM 물리 용량은 ~4 GiB지만 설계 주소공간은 1 GiB.

## 가설
1. (주) DRAM 트레이닝 미완료 상태에서 BIST를 돌려 읽기가 불안정 → 데이터 손상. 초기화가 끝나면 해소될 수 있음.
2. SO-DIMM/슬롯 접촉 또는 SPD 기반 타이밍이 이 모듈에 marginal → 트레이닝이 간헐적으로 실패.
3. 위 두 구간이 실제 DIMM 결함(약한 셀/row)일 가능성.

## 다음 선택지
- A. BIOS 콘솔로 초기화 재실행/진단 (`bios_console.py` → `reboot`)
- B. 보드 전원 재투입(콜드 리셋) 후 안정 상태에서 재측정
- C. 빌드 옵션 변경 재빌드 (`--keep-going-on-dram-error`, `--sys-clk-freq`, `--module` 등)
- D. 게이트 C를 우회하고 rowhammer 실험으로 진행(두 결함 구간을 관찰 대상으로 활용)

## 산출물
- `results/bist-run2.log`, `results/bist-run3.log`, `results/bist-run4.log`, `results/mem-run1.log`, `results/mem-run2.log`

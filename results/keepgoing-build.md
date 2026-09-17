# `--keep-going-on-dram-error` 빌드 결과 (2026-09-16 20:3x)

## 수행
```sh
PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH \
  make build TARGET=zcu104 ARGS="--from-spd build/zcu104/spd.bin --keep-going-on-dram-error"
```
- exit 0, `All user specified timing constraints are met`, `write_bitstream completed successfully`
- SPD 사용 확인(`sdram_spd.init` 1회), bitstream sha256 = `7403749a1f2a8019716c234cf138e5f7fd72095d98fd20e1088593b4324ba56d`
- JTAG 재프로그래밍(20:33:22) → ident `git: 2ab8a67... 2026-09-16 20:23:13`
- 콘솔 드레인/캡처: `build/bios_keepgoing.log`

## 결과: 여전히 실패, 옵션 효과 없음
- write leveling 출력이 **기본 모듈/SPD 빌드와 동일**:
  - `m6: |11111111110000000000000011111111| delay: 00`
  - Cmd/Clk 스캔 0 → 64 → 128 → 192 → 0 반복
- `ddrctrl_init_done = 0`, `ddrctrl_init_error = 0`
- → `--keep-going-on-dram-error`는 **write leveling 실패를 건너뛰지 못함**

## 지금까지 배제된 가설
| 가설 | 결과 |
| --- | --- |
| SPD 설정이 원인 | 배제 (기본 모듈도 동일 실패) |
| 소프트 재부팅으로 해결 | 배제 |
| 드레인이 느려서 미완료 | 배제 (31,251 B 드레인에도 `init_done=0`) |
| `--keep-going-on-dram-error`로 우회 | 배제 (효과 없음) |
| refresh 옵션과 관련 | 배제 (leveling은 그 이전 단계) |

## 남은 원인 후보
1. **하드웨어**: SO-DIMM 접촉/슬롯, 또는 특정 DQ 바이트 레인(m6) 결함, 또는 보드 리비전/PHY 배선 문제
   - BIOS가 SPD도 못 읽음(`Couldn't read SDRAM size from the SPD`) → 모듈 접촉/SPD 경로도 의심
2. **PHY 클럭/탭 설정**: `--iodelay-clk-freq`, `--sys-clk-freq`, `--speedgrade`

## 확인 방법
```sh
# 보드 상태 확인 (재프로그래밍/전원 후)
sudo -n venv/bin/litex_server --uart --uart-port /dev/ttyUSB3 --uart-baudrate 1000000 &
TARGET=zcu104 venv/bin/python build/drain_fast.py 300     # init_done 확인
```

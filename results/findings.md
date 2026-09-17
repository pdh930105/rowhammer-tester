# ZCU104 DDR4 Rowhammer Tester — 실행 결과 및 진단 (2026-09-16)

계획: `~/.commandcode/plans/zcu104-ddr4-rowhammer-execution.md` (end-to-end, UARTBone 우선)
상태 파일 요약: 게이트 A/B 통과, 게이트 C에서 **DRAM write leveling 미수렴** 문제로 중단.

---

## 게이트별 결과

| 게이트 | 항목 | 결과 |
| --- | --- | --- |
| A | SPD 기반 bitstream 빌드 + timing/DRC | **PASS** |
| B | JTAG 임시 프로그래밍 | **PASS** |
| C | UARTBone 식별/DRAM·BIST 검증 | **FAIL (BIST)** — version.py는 PASS |
| D | microSD 영구 부팅 | 미실행 (물리 조작 필요) |
| E | Rowhammer smoke test | 미실행 (게이트 C 미통과) |

### 게이트 A — PASS
- `xilinx_zcu104.bit` 생성 (19,311,210 bytes), Vivado exit 0
- `All user specified timing constraints are met`, DRC 0 Errors, `write_bitstream completed successfully`
- SPD 사용 확인: `xilinx_zcu104_sdram_spd.init is read successfully`
- 해시/세부: `results/manifest.txt`

### 게이트 B — PASS
- `program_hw_devices` 성공, `End of startup status: HIGH`
- JTAG 체인: `xczu7_0 arm_dap_1` 인식

### 게이트 C — FAIL (BIST)
- `version.py` PASS: `Row Hammer Tester SoC on xczu7ev-ffvc1156-2-i, git: 2ab8a67... 2026-09-16 17:29:22`
- `mem_bist.py --test-memory` FAIL: 대량 오류 후 통신 두절(브리지 꼬임)

---

## 근본 원인: BIOS DRAM write leveling 미수렴

BIOS 콘솔 로그(`results/bios_console.log`)에서 확인:

```
Couldn't read SDRAM size from the SPD, defaulting to 256 MB.
SDRAM: 256.0MiB 64-bit @ 1000MT/s (CL-9 CWL-9)
MAIN-RAM: 1.0GiB

Initializing SDRAM @0x40000000...
Switching SDRAM to software control.
Write leveling:
  ...
  m6: |11111111110000000000000011111111| delay: 00     <-- leveling 실패
  Cmd/Clk delay: 0 → 64 → 128 → 192 → 0  ...             <-- 무한 반복, 수렴 안 함
```

- write leveling이 Cmd/Clk delay를 0→64→128→192로 스캔한 뒤 다시 0으로 돌아가 **무한 루프**에 빠짐
- 그 결과 `ddrctrl_init_done = 0`이 영원히 유지됨(초기화 미완료)
- 일부 모듈(m6 등)은 `delay: 00`으로 유효 지연을 못 찾음

### 이로 인한 증상 (직접 측정)
- BIST writer(512-bit DMA)가 64바이트 전송마다 **앞부분만 기록**되고 나머지는 미기록(이전 값 유지)
  - 64바이트 블록 내용 예: `AAAAAAAA AAAAAAAA 00000000 ... FFFFFFFF` (기록된 접두부가 실행마다 16B→8B로 달라짐)
- BIST reader가 읽은 DRAM 값과 Wishbone 경로로 읽은 값이 **동일** → 리더 자체는 정상, DRAM 내용이 실제로 불완전
- SoC gateware에는 데이터 폭 불일치 없음(`assert pattern_data_width == dram_*_port.data_width`, `pattern_data_width=512`)
- 패턴 메모리 자체는 정상(CSR로 되읽으면 16×`0xAAAAAAAA`)

즉 **software 데이터 경로가 아니라 PHY write 캘리브레이션(write leveling) 실패**가 원인.

---

## 부수적으로 확인된 운용상 주의점

1. **BIOS 콘솔을 드레인하지 않으면 DRAM init이 진행되지 않음**
   - BIOS가 crossover UART로 대량(수 KB) 로그를 출력하고, 호스트가 읽지 않으면 진행이 멈춤
   - `mem.py` / `bios_console.py`가 콘솔을 드레인함. 빠른 드레인은 바이트 유실(garble) 가능
2. **BIST reader 에러 고착**
   - reader가 에러에서 멈추면(`skip_fifo=0`) `reader_ready=0`으로 고착 → `hw_memtest`의 `assert reader_ready==1` 실패
   - 해제 방법: `reader_skip_fifo=1` 후 `reader_error_continue` 반복 write (진단 스크립트 `build/diag_reader.py`)
3. **UARTBone 브리지 꼬임 시 복구**
   - `Didn't get a response from the board` 발생 시 SoC는 살아있고 litex_server만 꼬인 경우가 있음 → litex_server 재시작으로 복구됨
4. **Ethernet 불가**: 보드는 `192.168.100.50`, 호스트 `enp4s0`는 `163.152.172.150/24` → ping 실패. 계획대로 UARTBone 사용
5. **시리얼 장치**: `/dev/ttyUSB1`(PS 콘솔), `/dev/ttyUSB3`(UARTBone). `ttyUSB0`은 JTAG 채널 점유 시 미노출. `pdh`가 `dialout` 미가입이라 `sudo -n` 사용
6. **main_ram 크기 = 1 GiB**(`max_sdram_size` 기본 0x40000000), DMA 전송 단위 = 64 bytes
7. ZCU104는 `make upload`/`make flash` 불가(의도적 exit 1) → 수동 JTAG/SD

---

## 다음 단계 (사용자 결정 필요)

1. **DRAM 캘리브레이션 해결** (게이트 C 통과의 전제)
   - SPD를 BIOS가 못 읽는 문제 확인: `spd_eeprom.py`로 SPD/I2C 경로 점검, 필요 시 커밋 `2ab8a67`의 SPD 처리 재검토
   - `--sys-clk-freq`(현재 125 MHz → 1000 MT/s) 또는 speedgrade/`--module` 조합을 바꿔 write leveling 재시도
   - SO-DIMM 접촉/슬롯, 보드 전원 상태 점검
2. 게이트 C 통과 후에만 D(영구 SD)·E(smoke test) 진행
3. 진단 산출물: `results/manifest.txt`, `results/bios_console.log`, `build/*.log`, `build/diag_*.py`

---

## 검증에 사용한 명령 (재현용)

```sh
# 빌드 (게이트 A)
PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH make build TARGET=zcu104 ARGS="--from-spd build/zcu104/spd.bin"

# JTAG (게이트 B)
PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH vivado -mode batch -nolog -nojournal -source build/program_jtag.tcl

# UARTBone 서버 + 검증 (게이트 C)
sudo -n venv/bin/litex_server --uart --uart-port /dev/ttyUSB3 --uart-baudrate 1000000
TARGET=zcu104 venv/bin/python rowhammer_tester/scripts/version.py
TARGET=zcu104 venv/bin/python build/drain_print.py 180 build/bios_console.log   # BIOS 콘솔 드레인
TARGET=zcu104 venv/bin/python build/diag_xcheck.py                              # BIST write vs Wishbone read
```

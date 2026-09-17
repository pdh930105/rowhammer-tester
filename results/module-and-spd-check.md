# SO-DIMM 재장착 후 점검 + 실제 모듈/SPD 확인 (2026-09-16 21:4x)

## 사용자 조치
- SO-DIMM 재장착 완료
- SW6 부트 모드 스위치 정상 확인
- 모듈 라벨: **M471A5244CB0-CTD** → 삼성 4GB DDR4 SO-DIMM, **PC4-2133P(DDR4-2133), 1Rx8**

## 점검 결과
1. **재장착 후에도 DRAM init은 동일 실패**
   - `ddrctrl_init_done = 0`, `init_error = 0`
   - write leveling: m6 `delay: 00` / Cmd·Clk 스캔 반복 (125 MHz SPD 빌드 재프로그래밍 후)
2. **실제 DIMM의 SPD를 I2C로 읽기 실패**
   - `i2c_write(0x74, 0x80)` (I2C 스위치 채널 선택) 단계에서 진행이 멈춤
   - I2C 워커 레지스터 상태: `i2c_state = 0x100` → FSM 상태 **1 = `RUN_I2C`** (트랜잭션이 끝나지 않고 걸려 있음)
     - 참고: `litex/soc/cores/i2c_worker.py:18` `I2CState` (IDLE=0, RUN_I2C=1, ABORT=9, …)
   - `write_fifo_state = 0xc0`, `read_fifo_state = 0x4c0` (pending 4), `i2c_ctrl = 0`
   - 즉 **I2C 버스가 응답하지 않아 SPD EEPROM 접근이 불가**
   - BIOS도 부팅 때부터 `Couldn't read SDRAM size from the SPD, defaulting to 256 MB`를 출력 → 재장착 전부터 SPD 읽기 실패는 존재했음(자체 시도와 무관한 증상)
3. **빌드에 사용한 `build/zcu104/spd.bin`은 이 모듈의 것이 아닐 가능성**
   - `spd_eeprom.py show` 결과 speedgrade가 **2666**으로 나오는데, 실제 모듈(M471A5244CB0-CTD)은 **DDR4-2133**
   - (기하구조 rowbits16/colbits10/banks8은 4Gbit x8 다이 기준으로는 일치)

## 해석
- DRAM 셀/버스는 어느 정도 동작(쓰고 읽으면 데이터가 나옴)하지만, **트레이닝이 끝나지 않고**(→ `init_done=0`) **I2C/SPD 경로도 응답하지 않음**
- 100 MHz에서는 8개 레인 전부 leveling이 되므로 특정 레인 사망은 아님 → 속도/신호 민감 + I2C hang은 **보드-DIMM 인터페이스(커넥터/슬롯/모듈) 쪽 문제**를 강하게 시사
- 모듈은 DDR4-2133(1Rx8)로 설계 속도(1000 MT/s 이하)보다 충분히 여유가 있어 성능 문제는 아님

## 권장 다음 단계 (우선순위)
1. **다른 DDR4 SO-DIMM으로 교체 테스트** — 가장 확실한 분리 방법(문서 기준 모듈: `MTA4ATF51264HZ` 등 1Rx8 DDR4)
2. **보드 리비전 확인** vs `third_party/litex-boards/litex_boards/platforms/xilinx_zcu104.py` DDR4 핀 정의
   - 해당 파일 주석에 "also AL17 AN17 AN16 for larger SODIMMs" 등 모듈 크기별 추가 핀 언급이 있음
3. 교체 후에도 동일하면 **보드(SO-DIMM 슬롯/커넥터) 문제**로 판단
4. SD 부팅 문제(SW6 확인했음에도 PL 미구성)는 별도로 점검 필요

## 현재 보드 상태
- 125 MHz SPD 빌드로 복원/재프로그래밍함 (bitstream sha256 `702d158f...`, ident `2ab8a67... 2026-09-16 17:29:22`)
- UARTBone 서버는 `/dev/ttyUSB4`에서 실행 중
- 참고: 리부트/전원 재투입 시 JTAG 구성이 사라지고 SD에서 PL이 안 올라오면 UARTBone이 죽음

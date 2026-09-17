# 근본 원인 및 해결책 — DRAM init 미완료 (2026-09-16 22:0x)

## 결론 (한 줄)
**하드웨어 문제가 아니었다.** FTDI USB-시리얼 드라이버의 `latency_timer` 기본값 **16 ms** 때문에
호스트가 BIOS 콘솔(crossover UART)을 ~**31 B/s**로밖에 드레인하지 못했고,
BIOS가 16바이트 콘솔 FIFO에서 블록되어 **DRAM 트레이닝이 끝나지 못했다**(`ddrctrl_init_done=0`).
`latency_timer=1`로 낮추자 드레인이 **~16배 빨라져(≈500 B/s)** 트레이닝이 완료되고 DRAM이 정상 동작했다.

## 증상 → 원인
| 증상 | 실제 원인 |
| --- | --- |
| `ddrctrl_init_done = 0` (재부팅/재빌드/재장착 후에도 동일) | BIOS가 콘솔 출력에서 블록 → 트레이닝 미완료 |
| write leveling에서 m6만 `delay: 00`, Cmd/Clk 스캔 반복 | 미완료 상태의 트레이닝을 계속 관찰한 결과(트레이닝 자체는 재시도/진행 중) |
| BIST(512-bit DMA) 쓰기가 64B 중 앞 16B만 기록 | PHY가 정상 캘리브레이션되지 않은 상태의 결과 |
| `Couldn't read SDRAM size from the SPD` | 트레이닝 미완료로 BIOS가 정상 콘솔 단계에 도달하지 못함 |
| `Didn't get a response from the board` (간헐) | 16 ms 지연 + 대량 CSR 접근으로 인한 타임아웃 |

## 결정적 측정
```sh
# 측정: 모든 CSR/메모리 접근이 정확히 16 ms
ctrl_scratch.read():      200 ops -> 16000 us/op
uart_xover_rxtx.read():   200 ops -> 16000 us/op
wb.read(main_ram, 16):    200 ops -> 16000 us/op

# FTDI latency timer 확인/수정
cat /sys/bus/usb-serial/devices/ttyUSB4/latency_timer     # 16
sudo sh -c 'echo 1 > /sys/bus/usb-serial/devices/ttyUSB4/latency_timer'

# 재측정: 1 ms/op (16배 향상)
ctrl_scratch.read():      200 ops -> 1001 us/op
```
→ `litex_server`/`comm_uart.py` 자체에는 지연이 없고, **USB-시리얼 드라이버의 16 ms 버퍼링**이 원인.

## 해결 후 검증 (게이트 C 통과)
- 콘솔 드레인: 300초에 40,576 bytes → **`ddrctrl_init_done = 1`**, `init_error = 0`
- `mem_bist.py --test-memory`: **exit 0, 모든 패턴 `Errors: 0`, `Test pattern OK!`** (캐시 우회 DMA 검증)
- `diag_dram.py` (Wishbone): 전 오프셋 0 errors
- 참고: `diag_xcheck.py`(BIST write + Wishbone read)에서 128/16384 불일치가 보였는데, 이는 L2(8 KiB) 캐시 영향이며 캐시를 우회하는 `mem_bist`에서는 0 errors

## 적용/재현 절차 (중요)
보드/`hw_server`를 재시작하거나 USB 재열거되면 `latency_timer`가 16으로 되돌아간다. 매번:
```sh
# 장치명은 매번 확인 (ttyUSB 번호가 바뀔 수 있음)
ls -l /dev/ttyUSB*
for d in /sys/bus/usb-serial/devices/ttyUSB*; do echo 1 | sudo tee $d/latency_timer; done

# 그 다음 UARTBone 서버 실행
sudo -n venv/bin/litex_server --uart --uart-port /dev/ttyUSB4 --uart-baudrate 1000000
```
영구 적용하려면 udev 규칙을 추가:
```
# /etc/udev/rules.d/99-ftdi-latency.rules
ACTION=="add", SUBSYSTEM=="usb-serial", DRIVER=="ftdi_sio", ATTR{latency_timer}="1"
```
그리고 DRAM 트레이닝이 완료될 때까지 **BIOS 콘솔을 드레인**해야 한다:
```sh
TARGET=zcu104 venv/bin/python build/drain_fast.py 300      # init_done=1 될 때까지
```
(현재 보드에서는 40 KB 드레인 후 `init_done=1` 달성)

## 정정
- 이전 기록(`results/phy-options.md`, `results/module-and-spd-check.md`)에서 하드웨어/I2C 의심으로 적은 부분은 **이 원인으로 설명됨**.
- `build/zcu104/spd.bin`은 실제 모듈(M471A5244CB0-CTD: 4GB 1Rx16, 8Gbit x16, 2666)과 **일치**함이 확인됨(1Rx16·8Gbit x16 → 8 banks/65536 rows/1024 cols, speedgrade 2666).

## 다음
- 게이트 D(microSD 영구 부팅), 게이트 E(Rowhammer smoke test) 진행 가능
- SD 부팅 문제는 별개(전원 투입 시 SD에서 PL 구성 여부) — SW6은 정상 확인됨

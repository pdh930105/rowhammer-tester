# PHY 옵션 실험 결과 (2026-09-16 20:5x~21:2x)

DRAM write leveling 실패를 PHY 설정으로 풀 수 있는지 3가지 시도. **결론: PHY 주파수 노브로는 해결되지 않음.**

## 1) `--iodelay-clk-freq 400e6` → 빌드 실패
```
ValueError: No PLL config found   (litex/soc/cores/clock/xilinx_common.py:141)
```
125 MHz 클럭 입력에서 MMCM이 pll4x(500 MHz)+idelay(400 MHz)+uart(125 MHz) 조합을 못 만듦.
실패 지점이 SoC 생성 단계라 Vivado까지 가지 않음(기존 `xilinx_zcu104.bit`는 무사, sha256 7403749a 유지).

## 2) `--iodelay-clk-freq 750e6` → 빌드 실패
동일하게 `No PLL config found`.
→ `--iodelay-clk-freq`는 사실상 125의 배수(500 MHz, 기본값) 외에는 사용 불가.

## 3) `--sys-clk-freq 100e6` (DRAM 1000→800 MT/s) → 빌드 성공하나 문제 미해결
- 빌드: exit 0, timing met, bitstream sha256 `c84bbb52bf8d6ca7d65133276648b0e2b20d2a41eb9e441d672fb2d1e8953220`
- **부작용(새 문제 유발)**: MMCM이 정확히 400 MHz를 못 만들어 IDELAYCTRL REFCLK가 402.778 MHz가 됨
  → `CRITICAL WARNING [Timing 38-470]` IDELAYE3/ODELAYE3의 `REFCLK_FREQUENCY=400 MHz`와 불일치(탭 보정 오차)
  (기본 125 MHz 빌드는 clkout1 = 정확히 500.000 MHz로 이 경고가 없음)
- JTAG 프로그래밍 후 ident `git: 2ab8a67... 2026-09-16 21:00:05`
- **write leveling**: `Cmd/Clk delay 0`에서 **8개 레인 전부 유효 지연 확보**(m0~m7: 336~339, m6=337) — 125 MHz에서 문제였던 m6가 여기서는 정상
  - 그러나 `Cmd/Clk delay 64/128/192`에서는 일부 레인이 다시 00
- **장시간 드레인 결과**: 1200초 동안 **25,001 bytes 드레인(20.8 B/s)** 했는데도 `ddrctrl_init_done = 0`
  - `init_error = 0`
  - 로그: `build/bios_sysclk100.log`

## 해석
- 레인 하나가 죽은 게 아님: 100 MHz에서 m6 포함 전 레인이 유효 → **레인 자체 결함은 아님**
- 그런데도 트레이닝이 끝나지 않고 BIOS가 계속 재시도 → 신호 마진/라우팅/핀맵 문제 또는 트레이닝 알고리즘의 수용 조건 문제
- 125 MHz에서 m6만 튀고, 100 MHz에서는 전 레인이 정상 → **속도에 민감한 링크 문제**(보드 라우팅/커넥터/모듈 특성) 가능성

## 현재 상태
- 보드에는 100 MHz 빌드가 올라가 있음(의도한 설정은 125 MHz SPD 빌드)
- 원래 125 MHz SPD 빌드는 `build/zcu104-spd-backup/`에 백업(bitstream sha256 702d158f...)

## 다음 후보
1. **보드 리비전 / 핀맵 확인**: `litex_boards.platforms.xilinx_zcu104` 제약과 실제 보드 리비전(revA/revC/rev1.0 등) 일치 여부
2. **SO-DIMM 재장착/교체**(물리) — 속도 민감 링크 문제면 접촉/모듈 교체로 해소될 수 있음
3. SD 부팅 문제(SW6 스위치 확인 필요)와 별개로 진행

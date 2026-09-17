# 기본 모듈 빌드 실험 결과 (2026-09-16 19:5x)

## 목적
`--from-spd`를 제거하고 기본 모듈(`MTA4ATF51264HZ`)로 재빌드해, DRAM leveling 실패가
**SPD 설정 때문인지 vs 보드/DIMM 문제인지** 분리.

## 수행
1. 기존 SPD 빌드 산출물 백업 → `build/zcu104-spd-backup/`
2. `PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH make build TARGET=zcu104` (ARGS 없음 = 기본 모듈)
   - exit 0, `All user specified timing constraints are met`, `write_bitstream completed successfully`
   - `sdram_spd.init` 사용 흔적 0건(SPD 미사용 확인)
   - bitstream sha256 = `b3d641e9b29ca1a5d10b0e1fb1299bdae42f7ef5f26516684fa94a6f27604352`
   - `litedram_settings.json`: geom 동일(bankbits3/rowbits16/colbits10), `tFAW=5`·`tCCD=1`만 SPD 버전과 상이
3. JTAG 재프로그래밍 → ident: `git: 2ab8a67... 2026-09-16 19:46:36`(새 빌드 로드 확인)
4. 콘솔 드레인/캡처(`build/bios_default_module.log`)

## 결과: **동일 실패** → SPD가 원인이 아님
- `Couldn't read SDRAM size from the SPD, defaulting to 256 MB.` (동일)
- write leveling:
  - `m6: |11111111100000000000000011111111| delay: 00`  ← **SPD 빌드와 동일하게 m6가 00**
  - Cmd/Clk 스캔 0 → 64 → 128 → 192 → 0 반복(수렴 안 함)
- `ddrctrl_init_done = 0`, `ddrctrl_init_error = 0`

## 해석
- 모듈 설정(SPD vs 기본)과 무관하게 **같은 바이트 레인(m6)에서 leveling이 실패**하고 스캔이 반복됨
- → 원인은 SPD/타이밍 설정이 아니라 **PHY 캘리브레이션 또는 하드웨어(DIMM/슬롯/보드)** 쪽

## 다음 후보
- **하드웨어**: 완전 콜드 파워사이클, SO-DIMM 재장착, 다른 DDR4 SO-DIMM으로 교체
- **PHY 빌드 옵션**: `--iodelay-clk-freq`, `--sys-clk-freq`, `--speedgrade`
- **`--keep-going-on-dram-error`**: 트레이닝 실패에도 init을 끝내고 쓰기 경로를 실제 검증

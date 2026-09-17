# ZCU104 DDR4 SO-DIMM Rowhammer Tester 작업 계획

## 1. 목표와 현재 상태

목표는 ZCU104에 장착된 DDR4 SO-DIMM의 실제 SPD 정보를 사용해 gateware를 빌드하고, 먼저 JTAG으로 임시 배포해 안전하게 검증한 뒤, 검증된 비트스트림을 microSD에 영구 반영하여 재현 가능한 Rowhammer 실험 환경을 만드는 것이다.

2026-09-16 현재 확인된 상태는 다음과 같다.

- 보드: Xilinx ZCU104 (`xczu7ev-ffvc1156-2-i`)
- JTAG: `localhost:3121/xilinx_tcf/Xilinx/41480A`에서 인식됨
- USB 직렬 포트: `/dev/ttyUSB0`~`/dev/ttyUSB3`
  - `/dev/ttyUSB1`: PS Linux 콘솔, 115200 baud
  - `/dev/ttyUSB3`: PL UARTBone, 1,000,000 baud
- SO-DIMM: DDR4, 약 4 GiB, 1 rank, x16 device, 64-bit bus, 2666 MT/s 등급
- SPD 원본: `build/zcu104/spd.bin` (256 bytes)
- Python 가상환경과 FPGA 도구 의존성 설치 완료
- fork 원격 저장소: `https://github.com/pdh930105/rowhammer-tester.git`
- 설정 개선 커밋: `2ab8a67 Improve ZCU104 setup reproducibility`
- 위 커밋은 `fork/main`에 push 완료
- 현재 로컬 `main`은 upstream `origin/main`보다 1개 커밋 앞서 있으나 `fork/main`과 일치함
- 보드 Ethernet은 현재 `NO-CARRIER`이므로 제어는 우선 UARTBone을 사용해야 함
- 전체 단위 테스트는 긴 DDR5 시뮬레이션 때문에 중단했으며, 중단 전 완료된 테스트는 통과함
- 다음 명령의 SPD 기반 Vivado 빌드가 현재 실행 중임. 같은 빌드를 중복 실행하지 말 것.

```sh
PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH \
make build TARGET=zcu104 ARGS="--from-spd build/zcu104/spd.bin"
```

## 2. 1단계: 현재 빌드 완료 및 산출물 검증

### 실행

1. 기존 `make`/Vivado 프로세스가 끝날 때까지 상태를 감시한다.

   ```sh
   ps -ef | rg '[m]ake build|[v]ivado'
   tail -f build/zcu104/gateware/vivado.log
   ```

2. 프로세스가 비정상 종료된 경우에만 위 SPD 기반 빌드 명령을 다시 실행한다.
3. 빌드가 끝나면 다음 산출물이 존재하는지 확인한다.

   ```sh
   test -s build/zcu104/gateware/xilinx_zcu104.bit
   test -s build/zcu104/csr.csv
   test -s build/zcu104/litedram_settings.json
   sha256sum build/zcu104/gateware/xilinx_zcu104.bit build/zcu104/spd.bin
   ```

4. Vivado 로그에서 오류와 타이밍 결과를 확인한다.

   ```sh
   rg -n 'ERROR:|CRITICAL WARNING:|Timing constraints are met|Timing constraints are not met' \
     build/zcu104/gateware/vivado.log
   ```

### 통과 조건

- Vivado가 exit code 0으로 종료됨
- `xilinx_zcu104.bit`가 생성되고 크기가 0보다 큼
- 치명적 DRC 오류가 없음
- 타이밍 제약이 충족됨
- 생성된 설정에 `build/zcu104/spd.bin`이 사용되었다는 로그가 남음

타이밍 실패, DRC 오류 또는 메모리 부족으로 종료되면 FPGA에 올리지 말고 해당 로그부터 분석한다.

## 3. 2단계: JTAG 임시 배포

microSD를 바로 덮어쓰기 전에 새 비트스트림을 JTAG으로 임시 로드한다. 이 단계는 현재 PL 구성을 변경하지만 flash나 microSD는 변경하지 않으므로 전원을 껐다 켜면 기존 부팅 구성이 복원된다.

### 사전 확인

- Vivado Hardware Manager에서 대상이 `xczu7_0`인지 확인한다.
- 사용 파일이 이번 빌드의 `build/zcu104/gateware/xilinx_zcu104.bit`인지 확인한다.
- 기존 빌드가 완전히 종료되었는지 확인한다.

### 배포 예시

```sh
PATH=/tools/xilinx/Vivado/2022.2/bin:$PATH vivado -mode batch -source /dev/stdin <<'TCL'
open_hw_manager
connect_hw_server -url localhost:3121
open_hw_target
set dev [lindex [get_hw_devices xczu7_0] 0]
set_property PROGRAM.FILE build/zcu104/gateware/xilinx_zcu104.bit $dev
program_hw_devices $dev
refresh_hw_device $dev
close_hw_manager
TCL
```

### 통과 조건

- `program_hw_devices`가 오류 없이 완료됨
- FPGA의 DONE 상태가 유지됨
- JTAG 체인에서 `xczu7_0`과 `arm_dap_1`이 계속 인식됨

## 4. 3단계: UARTBone 연결과 기본 기능 검증

Ethernet 링크가 없으므로 `/dev/ttyUSB3`의 UARTBone을 사용한다. `dialout` 그룹 변경은 새 로그인 세션부터 적용되므로 권한이 아직 반영되지 않았다면 해당 서버 명령에만 `sudo`를 사용한다.

### 터미널 A: LiteX 서버

```sh
venv/bin/litex_server --uart --uart-port /dev/ttyUSB3 --uart-baudrate 1000000
```

권한 오류가 있을 때만:

```sh
sudo -n venv/bin/litex_server --uart --uart-port /dev/ttyUSB3 --uart-baudrate 1000000
```

### 터미널 B: 보드 및 DRAM 검증

```sh
export TARGET=zcu104
venv/bin/python rowhammer_tester/scripts/version.py
venv/bin/python rowhammer_tester/scripts/mem_bist.py --test-memory
```

`mem_bist.py --test-memory`는 구성된 전체 메모리 범위에 여러 패턴을 쓰므로, 보드 DRAM에 보존할 데이터가 없는지 확인한 뒤 실행한다.

### 통과 조건

- `version.py`가 이번 빌드의 Rowhammer Tester 식별 문자열을 출력함
- DDR PHY training이 완료됨
- BIST의 모든 패턴에서 오류 수가 0임
- 통신 timeout 또는 CSR 주소 불일치가 없음

실패하면 먼저 다음 순서로 원인을 분리한다.

1. `/dev/ttyUSB3` 점유 프로세스와 권한 확인
2. UART baudrate가 1,000,000인지 확인
3. 호스트 스크립트가 `build/zcu104/csr.csv`를 사용하는지 확인
4. 새 bitstream과 생성 파일이 같은 빌드에서 나온 것인지 확인
5. DDR training 로그와 SPD CRC 확인

## 5. 4단계: 영구 부팅 구성

JTAG 검증을 통과한 비트스트림만 BOOT 파티션에 반영한다. ZCU104 부트로더가 기대하는 이름은 `zcu104.bit`이므로 생성 파일을 그 이름으로 복사한다.

Ethernet 링크가 복구된 경우:

```sh
ssh root@192.168.100.50 'mount /dev/mmcblk0p1 /boot'
scp build/zcu104/gateware/xilinx_zcu104.bit root@192.168.100.50:/boot/zcu104.bit.new
ssh root@192.168.100.50 \
  'cp /boot/zcu104.bit /boot/zcu104.bit.backup && mv /boot/zcu104.bit.new /boot/zcu104.bit && sync'
ssh root@192.168.100.50 reboot
```

Ethernet이 계속 `NO-CARRIER`이면 보드를 끈 뒤 microSD BOOT 파티션을 호스트에 마운트하여 기존 `zcu104.bit`을 백업하고 새 파일을 복사한다. 장치명은 `lsblk`로 확인하며 추측해서 `dd`나 포맷 명령을 실행하지 않는다.

재부팅 후 3단계의 `version.py`와 BIST를 다시 실행한다. 재부팅 후에도 통과해야 영구 배포 완료로 간주한다.

## 6. 5단계: Rowhammer 실험을 단계적으로 확대

처음부터 전체 DIMM을 대상으로 장시간 공격하지 않는다. 결과를 재현할 수 있도록 작은 범위와 낮은 read count에서 시작한다.

### 기준선 생성

```sh
export TARGET=zcu104
mkdir -p results/baseline
venv/bin/python rowhammer_tester/scripts/benchmark.py bist read
```

### 소규모 기능 시험

```sh
cd rowhammer_tester/scripts
../../venv/bin/python hw_rowhammer.py \
  --pattern 01_in_row \
  --all-rows --start-row 3 --nrows 8 \
  --read_count 10000 \
  --log-dir ../../results/smoke-001
```

### 점진적 확대

1. refresh가 켜진 상태로 기능과 로그 형식을 검증한다.
2. `read_count`를 `1e4`, `1e5`, `1e6` 순으로 늘린다.
3. row 범위를 작은 구간에서 확대한다.
4. 각 실험마다 bit flip 수, 주소, 실행 시간, SPD hash, bitstream hash, Git commit을 기록한다.
5. 정상 실험이 반복 재현된 뒤에만 `--no-refresh`를 사용한다.

`--no-refresh` 실험은 메모리 데이터 손상을 의도적으로 유발할 수 있다. 보드에서 중요 프로세스를 실행하지 않고, 온도와 전원 상태를 감시하며, 통신 불능이나 과열 징후가 나타나면 즉시 실험을 중단하고 보드를 재부팅한다.

## 7. 6단계: 재현성 정리와 Git 반영

실험 코드나 문서를 추가한 뒤에는 생성물과 사용자 파일을 커밋에 섞지 않는다.

현재 커밋 대상에서 제외해야 할 항목:

- `build/`
- `.commandcode/`
- `graphify-out/`
- `vivado_*.log`, `vivado_*.jou`, `vivado_*.backup.*`
- submodule 내부의 로컬 빌드 생성물
- 목적이 불분명한 `package.json`, `package-lock.json`

검증 명령:

```sh
git diff --check
git status --short
git diff --submodule=short
```

`plan.md`와 이후 의도적으로 수정한 소스/문서만 별도 커밋하고 fork로 push한다.

```sh
git add plan.md <의도적으로 수정한 파일들>
git commit -m "Document ZCU104 DDR4 validation plan"
git push fork main
```

## 8. 완료 기준

다음 조건이 모두 만족되면 환경 구성이 완료된 것으로 본다.

- 실제 SO-DIMM SPD 기반 bitstream 빌드 성공
- Vivado timing/DRC 통과
- JTAG 임시 프로그램 성공
- UARTBone에서 새 design identifier 확인
- DDR training 성공 및 BIST 오류 0
- microSD 영구 배포 후 재부팅 검증 성공
- 소규모 Rowhammer smoke test와 결과 로그 생성 성공
- 사용한 Git commit, SPD SHA-256, bitstream SHA-256, 명령, 실험 조건이 기록됨

현재 바로 수행할 다음 작업은 **실행 중인 Vivado 빌드가 끝날 때까지 감시하고 1단계의 산출물·타이밍 검증을 수행하는 것**이다.

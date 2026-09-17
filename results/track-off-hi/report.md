# Bit-flip tendency report

- input files: 4
  - `results/track-off-hi/bitflips_1789607162.078913.csv`: 19655 flips
  - `results/track-off-hi/bitflips_1789607910.290566.csv`: 110685 flips
  - `results/track-off-hi/bitflips_1789610145.729922.csv`: 329323 flips
  - `results/track-off-hi/bitflips_1789614740.638159.csv`: 676070 flips
- **total bit-flips: 1135733**
- victim rows affected: 16384
- victim (row, byte) cells: 675460
- addresses: 0x400022ae .. 0x7fffff81

## Top 5 victim rows

| row | flips |
| --- | --- |
| 2425 | 15077 |
| 1 | 14081 |
| 3 | 13851 |
| 14230 | 111 |
| 2810 | 109 |

## DQ byte lane (byte offset within the 64-bit bus word)

| value | flips | share |
| --- | --- | --- |
| 0 | 122019 | 10.7% |
| 1 | 151025 | 13.3% |
| 2 | 141336 | 12.4% |
| 3 | 170670 | 15.0% |
| 4 | 125550 | 11.1% |
| 5 | 157473 | 13.9% |
| 6 | 117602 | 10.4% |
| 7 | 150058 | 13.2% |

## Bit position within the byte

| value | flips | share |
| --- | --- | --- |
| 0 | 4232 | 0.4% |
| 1 | 253462 | 22.3% |
| 2 | 4104 | 0.4% |
| 3 | 254014 | 22.4% |
| 4 | 2426 | 0.2% |
| 5 | 316702 | 27.9% |
| 6 | 2406 | 0.2% |
| 7 | 298387 | 26.3% |

## Flip direction (expected -> observed)

- `1->0`: 1122565 (98.8%)
- `0->1`: 13168 (1.2%)

## Bits flipped per byte cell (single/double/triple flip bytes)

| run (csv) | byte cells | single | double | triple | 4+ |
| --- | --- | --- | --- | --- | --- |
| `bitflips_1789607162.078913.csv` | 18600 | 17603 | 942 | 52 | 3 |
| `bitflips_1789607910.290566.csv` | 109205 | 107825 | 1288 | 84 | 8 |
| `bitflips_1789610145.729922.csv` | 327538 | 325884 | 1531 | 115 | 8 |
| `bitflips_1789614740.638159.csv` | 673967 | 672014 | 1812 | 132 | 9 |
| **all runs (sum)** | | 1123326 | 5573 | 383 | 28 |

## Double-bit flips within a byte: adjacent vs non-adjacent

- byte cells with exactly two flipped bits: 5573
- **adjacent** (bit distance == 1): 294 (5.3%)
- **non-adjacent** (bit distance > 1): 5279 (94.7%)

| bit distance within byte | pairs | share |
| --- | --- | --- |
| 1 | 294 | 5.3% |
| 2 | 2315 | 41.5% |
| 3 | 1011 | 18.1% |
| 4 | 83 | 1.5% |
| 5 | 1307 | 23.5% |
| 6 | 40 | 0.7% |
| 7 | 523 | 9.4% |

## Bank distribution

- bank 0: 180388 (15.9%)
- bank 1: 134443 (11.8%)
- bank 2: 135124 (11.9%)
- bank 3: 132350 (11.7%)
- bank 4: 136835 (12.0%)
- bank 5: 138815 (12.2%)
- bank 6: 139435 (12.3%)
- bank 7: 138343 (12.2%)

## Top 5 (row, byte) cells

| row | byte_in_row | byte_lane | flips |
| --- | --- | --- | --- |
| 1 | 7848 | 0 | 16 |
| 3 | 4912 | 0 | 16 |
| 2425 | 388 | 4 | 16 |
| 1 | 1670 | 6 | 15 |
| 3 | 687 | 7 | 15 |


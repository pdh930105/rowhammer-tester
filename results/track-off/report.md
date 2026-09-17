# Bit-flip tendency report

- input files: 10
  - `results/track-off/bitflips_1789606962.298615.csv`: 75 flips
  - `results/track-off/bitflips_1789606968.803835.csv`: 2079 flips
  - `results/track-off/bitflips_1789606976.013772.csv`: 3298 flips
  - `results/track-off/bitflips_1789606983.954522.csv`: 4150 flips
  - `results/track-off/bitflips_1789606992.647837.csv`: 4829 flips
  - `results/track-off/bitflips_1789607002.130585.csv`: 5346 flips
  - `results/track-off/bitflips_1789607012.279796.csv`: 5815 flips
  - `results/track-off/bitflips_1789607023.291825.csv`: 6240 flips
  - `results/track-off/bitflips_1789607035.469661.csv`: 6654 flips
  - `results/track-off/bitflips_1789607049.451337.csv`: 7075 flips
- **total bit-flips: 45561**
- victim rows affected: 305
- victim (row, byte) cells: 6492
- addresses: 0x40010009 .. 0x7fe8e801

## Top 8 victim rows

| row | flips |
| --- | --- |
| 2425 | 16111 |
| 1 | 14707 |
| 3 | 14167 |
| 2631 | 7 |
| 3761 | 5 |
| 4693 | 5 |
| 7365 | 5 |
| 9583 | 5 |

## DQ byte lane (byte offset within the 64-bit bus word)

| value | flips | share |
| --- | --- | --- |
| 0 | 5622 | 12.3% |
| 1 | 6162 | 13.5% |
| 2 | 4853 | 10.7% |
| 3 | 5707 | 12.5% |
| 4 | 5617 | 12.3% |
| 5 | 6245 | 13.7% |
| 6 | 5331 | 11.7% |
| 7 | 6024 | 13.2% |

## Bit position within the byte

| value | flips | share |
| --- | --- | --- |
| 0 | 5905 | 13.0% |
| 1 | 4608 | 10.1% |
| 2 | 5624 | 12.3% |
| 3 | 5049 | 11.1% |
| 4 | 3398 | 7.5% |
| 5 | 8835 | 19.4% |
| 6 | 3243 | 7.1% |
| 7 | 8899 | 19.5% |

## Flip direction (expected -> observed)

- `1->0`: 27391 (60.1%)
- `0->1`: 18170 (39.9%)

## Bits flipped per byte cell (single/double/triple flip bytes)

| run (csv) | byte cells | single | double | triple | 4+ |
| --- | --- | --- | --- | --- | --- |
| `bitflips_1789606962.298615.csv` | 75 | 75 | 0 | 0 | 0 |
| `bitflips_1789606968.803835.csv` | 2008 | 1938 | 69 | 1 | 0 |
| `bitflips_1789606976.013772.csv` | 3144 | 2994 | 146 | 4 | 0 |
| `bitflips_1789606983.954522.csv` | 3885 | 3628 | 249 | 8 | 0 |
| `bitflips_1789606992.647837.csv` | 4478 | 4141 | 324 | 12 | 1 |
| `bitflips_1789607002.130585.csv` | 4928 | 4529 | 381 | 17 | 1 |
| `bitflips_1789607012.279796.csv` | 5327 | 4858 | 451 | 17 | 1 |
| `bitflips_1789607023.291825.csv` | 5712 | 5203 | 491 | 17 | 1 |
| `bitflips_1789607035.469661.csv` | 6064 | 5496 | 547 | 20 | 1 |
| `bitflips_1789607049.451337.csv` | 6439 | 5827 | 589 | 22 | 1 |
| **all runs (sum)** | | 38689 | 3247 | 118 | 6 |

## Double-bit flips within a byte: adjacent vs non-adjacent

- byte cells with exactly two flipped bits: 3247
- **adjacent** (bit distance == 1): 231 (7.1%)
- **non-adjacent** (bit distance > 1): 3016 (92.9%)

| bit distance within byte | pairs | share |
| --- | --- | --- |
| 1 | 231 | 7.1% |
| 2 | 1177 | 36.2% |
| 3 | 634 | 19.5% |
| 4 | 0 | 0.0% |
| 5 | 876 | 27.0% |
| 6 | 0 | 0.0% |
| 7 | 329 | 10.1% |

## Bank distribution

- bank 0: 45053 (98.9%)
- bank 1: 77 (0.2%)
- bank 2: 69 (0.2%)
- bank 3: 53 (0.1%)
- bank 4: 99 (0.2%)
- bank 5: 56 (0.1%)
- bank 6: 87 (0.2%)
- bank 7: 67 (0.1%)

## Top 8 (row, byte) cells

| row | byte_in_row | byte_lane | flips |
| --- | --- | --- | --- |
| 3 | 4912 | 0 | 33 |
| 3 | 3745 | 1 | 26 |
| 2425 | 6293 | 5 | 26 |
| 1 | 1670 | 6 | 25 |
| 1 | 3880 | 0 | 25 |
| 3 | 5997 | 5 | 25 |
| 1 | 7848 | 0 | 24 |
| 1 | 293 | 5 | 24 |


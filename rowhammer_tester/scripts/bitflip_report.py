#!/usr/bin/env python3
"""Bit-flip tendency report.

Reads the per-flip CSV logs produced by ``hw_rowhammer.py``/``rowhammer.py`` when
``--log-dir`` is given (each run writes ``bitflips_<timestamp>.csv``) and reports
the tendency of the observed bit-flips:

* hottest victim rows,
* DQ byte lane (byte index within the 64-bit bus word),
* bit position within the byte,
* flip direction (expected -> data),
* hottest (row, byte) cells.

The CSV is written by ``RowHammer.dump_bitflips`` and contains one row per single
bit-flip with columns: row, bank, col, byte_in_row, byte_lane, bit_in_byte,
flip_addr, data_bit, expected_bit, direction, block_addr, block_word_index.
"""

import argparse
import csv
import glob
import os
from collections import Counter, defaultdict
from pathlib import Path

INT_COLUMNS = (
    "row",
    "bank",
    "col",
    "byte_in_row",
    "byte_lane",
    "bit_in_byte",
    "flip_addr",
    "data_bit",
    "expected_bit",
)


def collect_files(inputs):
    files = []
    for path in inputs:
        if os.path.isdir(path):
            files.extend(sorted(glob.glob(os.path.join(path, "**", "bitflips_*.csv"), recursive=True)))
        else:
            files.extend(sorted(glob.glob(path)))
    return files


def load_flips(files):
    flips = []
    per_file = {}
    for fname in files:
        count = 0
        with open(fname, newline="") as f:
            for row in csv.DictReader(f):
                for col in INT_COLUMNS:
                    row[col] = int(row[col])
                row["_file"] = fname
                flips.append(row)
                count += 1
        per_file[fname] = count
    return flips, per_file


def histogram(out, title, counter, keys, total):
    out(f"## {title}")
    out()
    out("| value | flips | share |")
    out("| --- | --- | --- |")
    for key in keys:
        count = counter.get(key, 0)
        out(f"| {key} | {count} | {100.0 * count / max(total, 1):.1f}% |")
    out()


def build_report(flips, per_file, top):
    out_lines = []

    def out(line=""):
        out_lines.append(line)

    out("# Bit-flip tendency report")
    out()
    out(f"- input files: {len(per_file)}")
    for fname, count in per_file.items():
        out(f"  - `{fname}`: {count} flips")
    total = len(flips)
    out(f"- **total bit-flips: {total}**")
    if total == 0:
        return "\n".join(out_lines) + "\n"

    rows = Counter(f["row"] for f in flips)
    cells = Counter((f["row"], f["byte_in_row"]) for f in flips)
    out(f"- victim rows affected: {len(rows)}")
    out(f"- victim (row, byte) cells: {len(cells)}")
    out(f"- addresses: 0x{min(f['flip_addr'] for f in flips):08x} .. 0x{max(f['flip_addr'] for f in flips):08x}")
    out()

    out(f"## Top {top} victim rows")
    out()
    out("| row | flips |")
    out("| --- | --- |")
    for row, count in rows.most_common(top):
        out(f"| {row} | {count} |")
    out()

    histogram(
        out,
        "DQ byte lane (byte offset within the 64-bit bus word)",
        Counter(f["byte_lane"] for f in flips),
        range(8),
        total,
    )
    histogram(
        out,
        "Bit position within the byte",
        Counter(f["bit_in_byte"] for f in flips),
        range(8),
        total,
    )

    out("## Flip direction (expected -> observed)")
    out()
    for direction, count in Counter(f["direction"] for f in flips).most_common():
        out(f"- `{direction}`: {count} ({100.0 * count / total:.1f}%)")
    out()

    # How many *distinct bits* flipped inside the same byte cell (same row, same byte).
    # Computed per input file, i.e. per single experiment run.
    out("## Bits flipped per byte cell (single/double/triple flip bytes)")
    out()
    out("| run (csv) | byte cells | single | double | triple | 4+ |")
    out("| --- | --- | --- | --- | --- | --- |")
    per_file_bits = {}
    for f in flips:
        per_file_bits.setdefault(f["_file"], set()).add((f["row"], f["byte_in_row"], f["bit_in_byte"]))
    aggregate = Counter()
    for fname, keys in per_file_bits.items():
        per_cell = Counter((row, byte) for row, byte, _bit in keys)
        hist = Counter(per_cell.values())
        for k, v in hist.items():
            aggregate[k] += v
        out(
            f"| `{os.path.basename(fname)}` | {len(per_cell)} | {hist.get(1, 0)} | {hist.get(2, 0)}"
            f" | {hist.get(3, 0)} | {sum(v for k, v in hist.items() if k >= 4)} |"
        )
    if per_file_bits:
        out(
            f"| **all runs (sum)** | | {aggregate.get(1, 0)} | {aggregate.get(2, 0)}"
            f" | {aggregate.get(3, 0)} | {sum(v for k, v in aggregate.items() if k >= 4)} |"
        )
    out()

    # Among byte cells with exactly two flipped bits: adjacent vs non-adjacent bit pairs.
    out("## Double-bit flips within a byte: adjacent vs non-adjacent")
    out()
    adjacent = non_adjacent = 0
    distances = Counter()
    for _fname, keys in per_file_bits.items():
        per_cell_bits = defaultdict(set)
        for row, byte, bit in keys:
            per_cell_bits[(row, byte)].add(bit)
        for bits in per_cell_bits.values():
            if len(bits) == 2:
                low, high = sorted(bits)
                distances[high - low] += 1
                if high - low == 1:
                    adjacent += 1
                else:
                    non_adjacent += 1
    total_pairs = adjacent + non_adjacent
    out(f"- byte cells with exactly two flipped bits: {total_pairs}")
    out(
        f"- **adjacent** (bit distance == 1): {adjacent}"
        f" ({100.0 * adjacent / max(total_pairs, 1):.1f}%)"
    )
    out(
        f"- **non-adjacent** (bit distance > 1): {non_adjacent}"
        f" ({100.0 * non_adjacent / max(total_pairs, 1):.1f}%)"
    )
    out()
    if total_pairs:
        out("| bit distance within byte | pairs | share |")
        out("| --- | --- | --- |")
        for distance in range(1, 8):
            count = distances.get(distance, 0)
            out(f"| {distance} | {count} | {100.0 * count / total_pairs:.1f}% |")
        out()

    out("## Bank distribution")
    out()
    for bank, count in sorted(Counter(f["bank"] for f in flips).items()):
        out(f"- bank {bank}: {count} ({100.0 * count / total:.1f}%)")
    out()

    out(f"## Top {top} (row, byte) cells")
    out()
    out("| row | byte_in_row | byte_lane | flips |")
    out("| --- | --- | --- | --- |")
    for (row, byte_in_row), count in cells.most_common(top):
        out(f"| {row} | {byte_in_row} | {byte_in_row % 8} | {count} |")
    out()

    return "\n".join(out_lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="+", help="bitflips_*.csv files, globs or directories")
    parser.add_argument("--top", type=int, default=20, help="Number of hot entries to list (default: 20)")
    parser.add_argument("--out", help="Write the markdown report to this file")
    parser.add_argument("--csv-out", help="Write all flips (combined) to this CSV file")
    args = parser.parse_args()

    files = collect_files(args.inputs)
    if not files:
        parser.error("no bitflips_*.csv files found for the given inputs")

    flips, per_file = load_flips(files)
    report = build_report(flips, per_file, args.top)
    print(report)

    if args.out:
        Path(args.out).write_text(report)
        print(f"report written to: {args.out}")

    if args.csv_out and flips:
        with open(args.csv_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(flips[0].keys()))
            writer.writeheader()
            writer.writerows(flips)
        print(f"combined flips written to: {args.csv_out}")


if __name__ == "__main__":
    main()

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
import json
import os
import re
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
                if row.get("read_count") not in (None, ""):
                    row["read_count"] = int(row["read_count"])
                else:
                    row["read_count"] = None
                row["_file"] = fname
                flips.append(row)
                count += 1
        per_file[fname] = count
    return flips, per_file


def run_summary(run_flips):
    """Per-run statistics used for the intensity (read_count) summary CSV."""

    distinct = {(f["row"], f["byte_in_row"], f["bit_in_byte"]) for f in run_flips}
    per_cell = defaultdict(set)
    for row, byte, bit in distinct:
        per_cell[(row, byte)].add(bit)
    hist = Counter(len(bits) for bits in per_cell.values())

    adjacent = non_adjacent = 0
    for bits in per_cell.values():
        if len(bits) == 2:
            low, high = sorted(bits)
            if high - low == 1:
                adjacent += 1
            else:
                non_adjacent += 1

    return {
        "flips": len(run_flips),
        "byte_cells": len(per_cell),
        "single": hist.get(1, 0),
        "double": hist.get(2, 0),
        "triple": hist.get(3, 0),
        "four_plus": sum(count for n, count in hist.items() if n >= 4),
        "double_adjacent": adjacent,
        "double_non_adjacent": non_adjacent,
    }


def resolve_read_counts(files):
    """Maps each bitflips CSV to the read_count of its run.

    Uses the read_count column when present, otherwise falls back to matching the
    CSVs (in creation order) with the read_count keys of the error_summary JSON.
    """

    mapping = {}
    for fname in files:
        directory = os.path.dirname(fname) or "."
        jsons = sorted(glob.glob(os.path.join(directory, "error_summary_*.json")))
        counts = []
        if jsons:
            with open(jsons[-1]) as f:
                counts = sorted(int(k) for k in json.load(f))
        if not counts:
            # No summary yet (run still in progress): read the swept counts from the log.
            logs = sorted(glob.glob(os.path.join(directory, "run.log")))
            if logs:
                with open(logs[-1], errors="ignore") as f:
                    raw = [
                        int(float(m))
                        for m in re.findall(r"read_count:\s*([0-9.eE+]+)", f.read())
                    ]
                    for value in raw:  # collapse repeated prints of the same count
                        if value not in counts:
                            counts.append(value)
        siblings = sorted(glob.glob(os.path.join(directory, "bitflips_*.csv")))
        if counts and fname in siblings:
            # The CSVs are written in the same order as the read_counts are swept, so
            # map by position (the run may not have written its summary JSON yet).
            index = siblings.index(fname)
            mapping[fname] = counts[index] if index < len(counts) else None
        else:
            mapping[fname] = None
    return mapping


def write_summary_csv(path, flips, files, read_counts):
    columns = [
        "read_count",
        "flips",
        "byte_cells",
        "single",
        "double",
        "triple",
        "four_plus",
        "double_adjacent",
        "double_non_adjacent",
        "non_adjacent_share_percent",
        "file",
    ]
    rows = []
    for fname in files:
        stats = run_summary([f for f in flips if f["_file"] == fname])
        read_count = None
        for f in flips:
            if f["_file"] == fname and f["read_count"] is not None:
                read_count = f["read_count"]
                break
        if read_count is None:
            read_count = read_counts.get(fname)
        pairs = stats["double_adjacent"] + stats["double_non_adjacent"]
        stats["read_count"] = read_count if read_count is not None else ""
        stats["non_adjacent_share_percent"] = (
            f"{100.0 * stats['double_non_adjacent'] / pairs:.1f}" if pairs else ""
        )
        stats["file"] = os.path.basename(fname)
        rows.append(stats)

    rows.sort(key=lambda r: (r["read_count"] == "", r["read_count"]))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    return rows


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
    parser.add_argument(
        "--summary-csv",
        help="Write a per-run summary CSV (one row per read_count: single/double/triple/4+"
        " flip bytes and adjacent/non-adjacent double-bit pairs)",
    )
    args = parser.parse_args()

    files = collect_files(args.inputs)
    if not files:
        parser.error("no bitflips_*.csv files found for the given inputs")

    flips, per_file = load_flips(files)

    if args.summary_csv:
        rows = write_summary_csv(args.summary_csv, flips, files, resolve_read_counts(files))
        print(f"read_count | flips | byte cells | single | double | triple | 4+ | adj | non-adj")
        for r in rows:
            print(
                f"{str(r['read_count']):>10} | {r['flips']:>6} | {r['byte_cells']:>10}"
                f" | {r['single']:>6} | {r['double']:>6} | {r['triple']:>6} | {r['four_plus']:>3}"
                f" | {r['double_adjacent']:>4} | {r['double_non_adjacent']:>7}"
            )
        print(f"summary written to: {args.summary_csv}")

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

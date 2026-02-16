#!/usr/bin/env python3
"""
Subsample MSA files to target depths for Experiment 4.

Reads A3M-format MSAs and produces subsampled versions at specified depth
levels, preserving the query sequence as the first entry.

Supports deterministic subsampling via seed for reproducibility, and
diversity-weighted subsampling for better coverage.
"""

import argparse
import os
import random
import sys
from pathlib import Path

import yaml


def parse_a3m(filepath: str) -> list[tuple[str, str]]:
    """Parse an A3M file into a list of (header, sequence) tuples."""
    entries = []
    header = None
    seq_lines = []

    with open(filepath) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if header is not None:
                    entries.append((header, "".join(seq_lines)))
                header = line
                seq_lines = []
            elif header is not None:
                seq_lines.append(line)
        if header is not None:
            entries.append((header, "".join(seq_lines)))

    return entries


def write_a3m(entries: list[tuple[str, str]], filepath: str):
    """Write entries to an A3M file."""
    with open(filepath, "w") as f:
        for header, seq in entries:
            f.write(f"{header}\n{seq}\n")


def compute_sequence_identity(seq1: str, seq2: str) -> float:
    """Compute fraction of identical positions (ignoring gaps)."""
    matches = 0
    aligned = 0
    for a, b in zip(seq1, seq2):
        if a != "-" and b != "-":
            aligned += 1
            if a == b:
                matches += 1
    return matches / max(aligned, 1)


def subsample_random(
    entries: list[tuple[str, str]], target_depth: int, seed: int = 42
) -> list[tuple[str, str]]:
    """Random subsampling preserving query as first entry."""
    query = entries[0]
    rest = entries[1:]

    rng = random.Random(seed)
    if target_depth <= 1:
        return [query]
    elif target_depth - 1 >= len(rest):
        return entries  # Not enough sequences to subsample
    else:
        selected = rng.sample(rest, target_depth - 1)
        return [query] + selected


def subsample_diverse(
    entries: list[tuple[str, str]], target_depth: int, seed: int = 42
) -> list[tuple[str, str]]:
    """
    Diversity-weighted subsampling: greedily select sequences that maximize
    coverage by picking sequences most different from those already selected.
    """
    if target_depth <= 1:
        return [entries[0]]
    if target_depth >= len(entries):
        return entries

    query = entries[0]
    rest = entries[1:]
    rng = random.Random(seed)

    # Start with a random seed sequence from rest
    selected_indices = [rng.randint(0, len(rest) - 1)]
    remaining = set(range(len(rest))) - set(selected_indices)

    while len(selected_indices) < target_depth - 1 and remaining:
        # Find sequence most different from all selected
        best_idx = None
        best_min_dist = -1

        # Sample a subset for efficiency on large MSAs
        candidates = list(remaining)
        if len(candidates) > 500:
            candidates = rng.sample(candidates, 500)

        for idx in candidates:
            min_identity = min(
                compute_sequence_identity(rest[idx][1], rest[sel][1])
                for sel in selected_indices
            )
            # We want minimum identity to be maximized (= most different)
            distance = 1.0 - min_identity
            if distance > best_min_dist:
                best_min_dist = distance
                best_idx = idx

        if best_idx is not None:
            selected_indices.append(best_idx)
            remaining.discard(best_idx)
        else:
            break

    selected = [rest[i] for i in selected_indices]
    return [query] + selected


def subsample_all_depths(
    input_a3m: str,
    depths: list[int],
    output_dir: str,
    prefix: str = "",
    method: str = "random",
    seed: int = 42,
):
    """Subsample an MSA at multiple depth levels."""
    entries = parse_a3m(input_a3m)
    total = len(entries)
    print(f"Input MSA: {total} sequences from {input_a3m}")

    os.makedirs(output_dir, exist_ok=True)

    subsample_fn = subsample_diverse if method == "diverse" else subsample_random

    for depth in depths:
        if depth >= total:
            print(f"  Depth {depth}: skipped (MSA only has {total} sequences)")
            continue

        subsampled = subsample_fn(entries, depth, seed)
        actual_depth = len(subsampled)

        outname = f"{prefix}depth_{depth}.a3m" if prefix else f"depth_{depth}.a3m"
        outpath = os.path.join(output_dir, outname)
        write_a3m(subsampled, outpath)
        print(f"  Depth {depth}: wrote {actual_depth} sequences -> {outpath}")

    # Also write full MSA with consistent naming
    full_name = f"{prefix}depth_full.a3m" if prefix else "depth_full.a3m"
    full_path = os.path.join(output_dir, full_name)
    write_a3m(entries, full_path)
    print(f"  Depth full: wrote {total} sequences -> {full_path}")


def main():
    parser = argparse.ArgumentParser(description="Subsample MSAs to target depths")
    parser.add_argument("input_a3m", help="Input A3M file")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--prefix", default="", help="Filename prefix")
    parser.add_argument(
        "--depths",
        type=int,
        nargs="+",
        default=[1, 8, 16, 32, 64, 128, 256, 512, 1024],
        help="Target depths",
    )
    parser.add_argument(
        "--method",
        choices=["random", "diverse"],
        default="random",
        help="Subsampling method",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--config",
        type=str,
        help="YAML config with targets and depths (overrides other args)",
    )
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = yaml.safe_load(f)
        depths = config.get("msa_depths", args.depths)
        # Remove 'full' from depths list (handled separately)
        depths = [d for d in depths if isinstance(d, int)]
    else:
        depths = args.depths

    subsample_all_depths(
        args.input_a3m,
        depths,
        args.output_dir,
        args.prefix,
        args.method,
        args.seed,
    )


if __name__ == "__main__":
    main()

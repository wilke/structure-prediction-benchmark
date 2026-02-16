#!/usr/bin/env python3
"""
Compute MSA quality statistics: Neff, mean pairwise identity, coverage.

Reads A3M files and outputs a CSV with per-MSA quality metrics.
These metrics are used alongside raw depth in Experiment 4 to provide
meaningful x-axis values (log(Neff)) for depth-quality curves.

Usage:
    python scripts/compute_msa_stats.py --msa-dir data/msas/ --output data/msa_stats.csv
    python scripts/compute_msa_stats.py --msa-file data/msas/mmseqs2/1UBQ.a3m
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np


def parse_a3m(filepath: Path) -> tuple[str, list[str]]:
    """Parse an A3M file, return (query_sequence, list_of_aligned_sequences).

    A3M format: lowercase = insertions (removed for alignment),
    uppercase + '-' = aligned positions.
    """
    sequences = []
    current_seq = []

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq:
                    sequences.append("".join(current_seq))
                current_seq = []
            elif line:
                current_seq.append(line)
        if current_seq:
            sequences.append("".join(current_seq))

    if not sequences:
        return "", []

    query = sequences[0]

    # Convert A3M to aligned sequences (remove lowercase insertions)
    aligned = []
    for seq in sequences:
        aln_seq = "".join(c for c in seq if c.isupper() or c == "-")
        aligned.append(aln_seq)

    return query, aligned


def compute_pairwise_identity(seq1: str, seq2: str) -> float:
    """Compute sequence identity between two aligned sequences."""
    if len(seq1) != len(seq2):
        min_len = min(len(seq1), len(seq2))
        seq1 = seq1[:min_len]
        seq2 = seq2[:min_len]

    matches = 0
    aligned_positions = 0
    for a, b in zip(seq1, seq2):
        if a != "-" and b != "-":
            aligned_positions += 1
            if a == b:
                matches += 1

    if aligned_positions == 0:
        return 0.0
    return matches / aligned_positions


def compute_neff(aligned_sequences: list[str], identity_threshold: float = 0.8) -> float:
    """Compute effective number of sequences (Neff).

    Neff = sum(1 / cluster_size_i) for each sequence i,
    where cluster_size_i is the number of sequences within
    identity_threshold of sequence i (including itself).

    This measures the non-redundant information content of the MSA.
    """
    n = len(aligned_sequences)
    if n <= 1:
        return float(n)

    # For large MSAs, subsample for efficiency
    max_seqs_for_full = 2000
    if n > max_seqs_for_full:
        # Use a random subset for Neff estimation
        rng = np.random.default_rng(42)
        indices = rng.choice(n, max_seqs_for_full, replace=False)
        subset = [aligned_sequences[i] for i in indices]
        scale_factor = n / max_seqs_for_full
    else:
        subset = aligned_sequences
        scale_factor = 1.0

    m = len(subset)
    cluster_sizes = np.ones(m)

    for i in range(m):
        for j in range(i + 1, m):
            identity = compute_pairwise_identity(subset[i], subset[j])
            if identity >= identity_threshold:
                cluster_sizes[i] += 1
                cluster_sizes[j] += 1

    neff = np.sum(1.0 / cluster_sizes) * scale_factor
    return neff


def compute_coverage(query: str, aligned_sequences: list[str]) -> float:
    """Fraction of query positions covered by at least one non-gap character."""
    if not aligned_sequences or not query:
        return 0.0

    query_len = len(query.replace("-", ""))
    aln_len = len(aligned_sequences[0]) if aligned_sequences else 0

    if aln_len == 0:
        return 0.0

    covered = np.zeros(aln_len, dtype=bool)
    for seq in aligned_sequences[1:]:  # skip query itself
        for j, c in enumerate(seq[:aln_len]):
            if c != "-":
                covered[j] = True

    # Map alignment positions back to query positions
    query_positions_covered = 0
    query_pos = 0
    for j in range(min(aln_len, len(aligned_sequences[0]))):
        if aligned_sequences[0][j] != "-":
            if covered[j]:
                query_positions_covered += 1
            query_pos += 1

    return query_positions_covered / query_len if query_len > 0 else 0.0


def compute_mean_pairwise_identity(query: str, aligned_sequences: list[str],
                                    max_pairs: int = 5000) -> float:
    """Mean pairwise identity between query and all other sequences."""
    if len(aligned_sequences) <= 1:
        return 1.0

    others = aligned_sequences[1:]
    if len(others) > max_pairs:
        rng = np.random.default_rng(42)
        indices = rng.choice(len(others), max_pairs, replace=False)
        others = [others[i] for i in indices]

    identities = []
    query_aln = aligned_sequences[0]
    for seq in others:
        identities.append(compute_pairwise_identity(query_aln, seq))

    return float(np.mean(identities)) if identities else 1.0


def analyze_msa(filepath: Path) -> dict:
    """Compute all MSA quality metrics for a single A3M file."""
    query, aligned = parse_a3m(filepath)

    depth = len(aligned)
    if depth == 0:
        return {
            "file": filepath.name,
            "depth": 0,
            "neff": 0.0,
            "mean_pairwise_identity": 0.0,
            "coverage": 0.0,
            "query_length": 0,
        }

    neff = compute_neff(aligned)
    mean_id = compute_mean_pairwise_identity(query, aligned)
    coverage = compute_coverage(query, aligned)
    query_len = len(query.replace("-", ""))

    return {
        "file": filepath.name,
        "depth": depth,
        "neff": round(neff, 2),
        "mean_pairwise_identity": round(mean_id, 4),
        "coverage": round(coverage, 4),
        "query_length": query_len,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute MSA quality statistics (Neff, identity, coverage)"
    )
    parser.add_argument(
        "--msa-dir",
        type=Path,
        default=None,
        help="Directory containing A3M files (searched recursively)",
    )
    parser.add_argument(
        "--msa-file",
        type=Path,
        default=None,
        help="Single A3M file to analyze",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/msa_stats.csv"),
        help="Output CSV path",
    )
    parser.add_argument(
        "--identity-threshold",
        type=float,
        default=0.8,
        help="Sequence identity threshold for Neff clustering (default: 0.8)",
    )

    args = parser.parse_args()

    if args.msa_file:
        a3m_files = [args.msa_file]
    elif args.msa_dir:
        a3m_files = sorted(args.msa_dir.rglob("*.a3m"))
    else:
        print("ERROR: Provide --msa-dir or --msa-file", file=sys.stderr)
        sys.exit(1)

    if not a3m_files:
        print("No A3M files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {len(a3m_files)} MSA files...")

    rows = []
    for filepath in a3m_files:
        print(f"  {filepath.name} ...", end=" ", flush=True)
        stats = analyze_msa(filepath)

        # Infer MSA source from path
        path_str = str(filepath).lower()
        if "mmseqs2" in path_str:
            stats["msa_source"] = "mmseqs2"
        elif "jackhmmer" in path_str:
            stats["msa_source"] = "jackhmmer"
        else:
            stats["msa_source"] = "unknown"

        # Infer target from filename
        stem = filepath.stem
        # Try to extract PDB ID pattern
        import re
        match = re.search(r"(\d[a-zA-Z0-9]{3})", stem)
        stats["target_id"] = match.group(1).upper() if match else stem

        rows.append(stats)
        print(f"depth={stats['depth']}, Neff={stats['neff']:.1f}, "
              f"mean_id={stats['mean_pairwise_identity']:.3f}")

    # Write CSV
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "target_id", "msa_source", "file", "depth", "neff",
        "mean_pairwise_identity", "coverage", "query_length",
    ]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} entries to {args.output}")


if __name__ == "__main__":
    main()

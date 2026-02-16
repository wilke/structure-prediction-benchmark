#!/usr/bin/env python3
"""
Orchestrate MSA generation for all target proteins using multiple methods.

Generates MSAs via:
  1. MMseqs2 (fast, broad coverage via ColabFold server or local DB)
  2. JackHMMER (sensitive, iterative — AlphaFold2 native method)

Also converts Stockholm output from JackHMMER to A3M format for
compatibility with Boltz and Chai.

Usage:
  python generate_msas.py --config configs/targets_pilot.yaml --data-dir data
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def run_command(cmd: list[str], description: str = "", cwd: str = None) -> int:
    """Run a shell command with logging."""
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"  [{description}] {cmd_str}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [ERROR] {description} failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.returncode


def generate_mmseqs2_msa(
    fasta_path: str,
    output_a3m: str,
    database: str = None,
    sensitivity: float = 7.5,
    max_seqs: int = 10000,
    threads: int = 8,
    use_server: bool = True,
) -> bool:
    """Generate MSA using MMseqs2."""
    os.makedirs(os.path.dirname(output_a3m), exist_ok=True)

    if use_server:
        # Use ColabFold MMseqs2 API
        cmd = [
            "colabfold_search",
            fasta_path,
            database or "colabfold_db",
            os.path.dirname(output_a3m),
        ]
    else:
        # Use local MMseqs2
        tmp_dir = output_a3m + ".tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        result_prefix = output_a3m.replace(".a3m", "")

        cmd = [
            "mmseqs", "easy-search",
            fasta_path,
            database,
            result_prefix,
            tmp_dir,
            "-s", str(sensitivity),
            "--max-seqs", str(max_seqs),
            "--threads", str(threads),
            "--format-mode", "5",
        ]

    return run_command(cmd, f"MMseqs2 MSA") == 0


def generate_jackhmmer_msa(
    fasta_path: str,
    output_sto: str,
    database: str = "uniref90.fasta",
    iterations: int = 3,
    evalue: float = 0.0001,
    cpus: int = 8,
) -> bool:
    """Generate MSA using JackHMMER."""
    os.makedirs(os.path.dirname(output_sto), exist_ok=True)

    log_file = output_sto.replace(".sto", ".log")
    cmd = [
        "jackhmmer",
        "-N", str(iterations),
        "-E", str(evalue),
        "--incE", str(evalue),
        "--cpu", str(cpus),
        "-A", output_sto,
        "-o", log_file,
        fasta_path,
        database,
    ]

    return run_command(cmd, f"JackHMMER MSA") == 0


def convert_sto_to_a3m(sto_path: str, a3m_path: str) -> bool:
    """Convert Stockholm format MSA to A3M format."""
    sequences = {}
    with open(sto_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(("#", "//")):
                continue
            parts = line.split()
            if len(parts) == 2:
                name, seq = parts
                if name in sequences:
                    sequences[name] += seq
                else:
                    sequences[name] = seq

    if not sequences:
        print(f"  [WARN] No sequences parsed from {sto_path}", file=sys.stderr)
        return False

    os.makedirs(os.path.dirname(a3m_path), exist_ok=True)
    with open(a3m_path, "w") as f:
        for name, seq in sequences.items():
            f.write(f">{name}\n{seq}\n")

    print(f"  Converted {len(sequences)} sequences: {sto_path} -> {a3m_path}")
    return True


def load_targets(config_path: str) -> list[dict]:
    """Load targets from the manifest or config."""
    # Try manifest first (output of prepare_targets.py)
    manifest_path = Path(config_path).parent.parent / "data" / "targets.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)

    # Fall back to YAML config
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["targets"]


def main():
    parser = argparse.ArgumentParser(description="Generate MSAs for all target proteins")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/targets_pilot.yaml",
        help="Target configuration YAML",
    )
    parser.add_argument("--data-dir", type=str, default="data", help="Base data directory")
    parser.add_argument(
        "--mmseqs2-db",
        type=str,
        default=None,
        help="MMseqs2 database path (or use server if not provided)",
    )
    parser.add_argument(
        "--jackhmmer-db",
        type=str,
        default="uniref90.fasta",
        help="JackHMMER database path (UniRef90)",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["mmseqs2", "jackhmmer"],
        help="MSA generation methods to use",
    )
    parser.add_argument("--threads", type=int, default=8, help="CPU threads")
    parser.add_argument("--skip-existing", action="store_true", help="Skip existing MSA files")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    targets = load_targets(args.config)
    print(f"Generating MSAs for {len(targets)} targets using methods: {args.methods}")

    results = {"mmseqs2": {}, "jackhmmer": {}}

    for target in targets:
        pdb_id = target.get("pdb_id", target.get("target_id", "unknown"))
        chain = target.get("chain", "A")
        tag = f"{pdb_id.lower()}_chain{chain}"

        # Find FASTA file
        fasta = target.get("fasta", str(data_dir / f"{tag}.fasta"))
        if not os.path.exists(fasta):
            print(f"\n[SKIP] FASTA not found for {tag}: {fasta}")
            continue

        print(f"\n{'='*60}")
        print(f"Target: {tag}")

        # --- MMseqs2 ---
        if "mmseqs2" in args.methods:
            a3m_path = str(data_dir / "msas" / "mmseqs2" / f"{tag}.a3m")
            if args.skip_existing and os.path.exists(a3m_path):
                print(f"  [skip] MMseqs2 MSA exists: {a3m_path}")
            else:
                use_server = args.mmseqs2_db is None
                ok = generate_mmseqs2_msa(
                    fasta, a3m_path,
                    database=args.mmseqs2_db,
                    threads=args.threads,
                    use_server=use_server,
                )
                results["mmseqs2"][tag] = "success" if ok else "failed"

        # --- JackHMMER ---
        if "jackhmmer" in args.methods:
            sto_path = str(data_dir / "msas" / "jackhmmer" / f"{tag}.sto")
            a3m_path = str(data_dir / "msas" / "jackhmmer" / f"{tag}.a3m")

            if args.skip_existing and os.path.exists(a3m_path):
                print(f"  [skip] JackHMMER MSA exists: {a3m_path}")
            else:
                ok = generate_jackhmmer_msa(
                    fasta, sto_path,
                    database=args.jackhmmer_db,
                    cpus=args.threads,
                )
                if ok:
                    convert_sto_to_a3m(sto_path, a3m_path)
                results["jackhmmer"][tag] = "success" if ok else "failed"

    # Summary
    print(f"\n{'='*60}")
    print("MSA Generation Summary:")
    for method, status in results.items():
        if status:
            success = sum(1 for v in status.values() if v == "success")
            print(f"  {method}: {success}/{len(status)} succeeded")


if __name__ == "__main__":
    main()

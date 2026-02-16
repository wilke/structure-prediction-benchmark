#!/usr/bin/env python3
"""
Collect and aggregate comparison metrics from all experiments.

Reads JSON metric files from GoWe workflow outputs and assembles them
into consolidated CSV tables for analysis and plotting.
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path


METRIC_COLUMNS = [
    "target_id",
    "tool",
    "msa_condition",
    "msa_source",
    "msa_depth",
    "tm_score",
    "rmsd",
    "weighted_rmsd",
    "gdt_ts",
    "gdt_ha",
    "aligned_length",
    "seq_identity",
    "ss_agreement",
    "contact_jaccard",
    "mean_plddt_predicted",
    "mean_plddt_reference",
    "n_divergent_residues",
    # pLDDT direct metrics
    "plddt_high_conf_fraction",    # fraction of residues with pLDDT >= 70
    "plddt_low_conf_fraction",     # fraction of residues with pLDDT < 50
    "rmsd_high_conf",              # RMSD over high-confidence residues only
    "tm_score_high_conf",          # TM-score over high-confidence residues only
    "plddt_accuracy_correlation",  # Pearson r between per-residue pLDDT and 1/distance
]


def parse_metrics_json(filepath: Path) -> dict:
    """Parse a protein_compare JSON metrics file."""
    with open(filepath) as f:
        data = json.load(f)

    # Normalize field names (protein_compare may use various formats)
    result = {}
    field_map = {
        "tm_score": ["tm_score", "tmscore", "TM-score"],
        "rmsd": ["rmsd", "RMSD"],
        "weighted_rmsd": ["weighted_rmsd", "wrmsd"],
        "gdt_ts": ["gdt_ts", "GDT-TS", "gdt_ts_score"],
        "gdt_ha": ["gdt_ha", "GDT-HA", "gdt_ha_score"],
        "aligned_length": ["aligned_length", "n_aligned"],
        "seq_identity": ["seq_identity", "sequence_identity"],
        "ss_agreement": ["ss_agreement", "secondary_structure_agreement"],
        "contact_jaccard": ["contact_jaccard", "contact_similarity"],
        "mean_plddt_1": ["mean_plddt_1", "plddt_reference"],
        "mean_plddt_2": ["mean_plddt_2", "plddt_predicted"],
        "n_divergent_residues": ["n_divergent_residues", "divergent_residues"],
        "plddt_high_conf_fraction": ["plddt_high_conf_fraction", "high_confidence_fraction"],
        "plddt_low_conf_fraction": ["plddt_low_conf_fraction", "low_confidence_fraction"],
        "rmsd_high_conf": ["rmsd_high_conf", "rmsd_high_confidence"],
        "tm_score_high_conf": ["tm_score_high_conf", "tmscore_high_confidence"],
        "plddt_accuracy_correlation": ["plddt_accuracy_correlation", "confidence_calibration"],
    }

    for canonical, variants in field_map.items():
        for v in variants:
            if v in data:
                result[canonical] = data[v]
                break
        if canonical not in result:
            result[canonical] = None

    return result


def infer_metadata_from_path(filepath: Path) -> dict:
    """Infer target_id, tool, msa_condition from file path conventions."""
    parts = str(filepath).lower()

    # Infer tool
    tool = "unknown"
    for t in ["alphafold", "boltz", "chai", "esmfold"]:
        if t in parts:
            tool = t
            break

    # Infer MSA condition
    msa_condition = "default"
    if "no_msa" in parts or "nomsa" in parts:
        msa_condition = "no_msa"
    elif "mmseqs2" in parts:
        msa_condition = "with_msa"
    elif "jackhmmer" in parts:
        msa_condition = "with_msa"
    elif tool == "esmfold":
        msa_condition = "no_msa"

    # Infer MSA source
    msa_source = "none"
    if "mmseqs2" in parts:
        msa_source = "mmseqs2"
    elif "jackhmmer" in parts:
        msa_source = "jackhmmer"
    elif tool == "alphafold" and msa_condition != "no_msa":
        msa_source = "alphafold_internal"

    # Infer MSA depth
    msa_depth = "full"
    depth_match = re.search(r"depth[_-]?(\d+)", parts)
    if depth_match:
        msa_depth = depth_match.group(1)
    elif msa_condition == "no_msa":
        msa_depth = "1"

    # Infer target ID from filename
    target_id = filepath.stem
    target_match = re.search(r"(\d[a-z0-9]{3})", parts)
    if target_match:
        target_id = target_match.group(1).upper()

    return {
        "target_id": target_id,
        "tool": tool,
        "msa_condition": msa_condition,
        "msa_source": msa_source,
        "msa_depth": msa_depth,
    }


def collect_experiment_metrics(
    results_dir: Path,
    experiment: str = None,
    metadata_overrides: dict = None,
) -> list[dict]:
    """Collect all metrics JSON files from a results directory."""
    rows = []

    json_files = sorted(results_dir.rglob("*.json"))
    for jf in json_files:
        if "ranking" in jf.name or "timings" in jf.name or "confidence" in jf.name:
            continue  # Skip non-metrics JSONs

        try:
            metrics = parse_metrics_json(jf)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [WARN] Skipping {jf}: {e}", file=sys.stderr)
            continue

        metadata = infer_metadata_from_path(jf)
        if metadata_overrides:
            metadata.update(metadata_overrides)

        row = {
            "target_id": metadata.get("target_id", ""),
            "tool": metadata.get("tool", ""),
            "msa_condition": metadata.get("msa_condition", ""),
            "msa_source": metadata.get("msa_source", ""),
            "msa_depth": metadata.get("msa_depth", ""),
            "tm_score": metrics.get("tm_score"),
            "rmsd": metrics.get("rmsd"),
            "weighted_rmsd": metrics.get("weighted_rmsd"),
            "gdt_ts": metrics.get("gdt_ts"),
            "gdt_ha": metrics.get("gdt_ha"),
            "aligned_length": metrics.get("aligned_length"),
            "seq_identity": metrics.get("seq_identity"),
            "ss_agreement": metrics.get("ss_agreement"),
            "contact_jaccard": metrics.get("contact_jaccard"),
            "mean_plddt_predicted": metrics.get("mean_plddt_2"),
            "mean_plddt_reference": metrics.get("mean_plddt_1"),
            "n_divergent_residues": metrics.get("n_divergent_residues"),
            "plddt_high_conf_fraction": metrics.get("plddt_high_conf_fraction"),
            "plddt_low_conf_fraction": metrics.get("plddt_low_conf_fraction"),
            "rmsd_high_conf": metrics.get("rmsd_high_conf"),
            "tm_score_high_conf": metrics.get("tm_score_high_conf"),
            "plddt_accuracy_correlation": metrics.get("plddt_accuracy_correlation"),
        }
        rows.append(row)

    return rows


def write_csv(rows: list[dict], output_path: Path):
    """Write aggregated metrics to CSV."""
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRIC_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect and aggregate experiment metrics")
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results",
        help="Root results directory from GoWe outputs",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/all_metrics.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--experiment",
        type=str,
        choices=["exp1", "exp2", "exp3", "exp4", "all"],
        default="all",
        help="Which experiment results to collect",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Results directory not found: {results_dir}", file=sys.stderr)
        sys.exit(1)

    all_rows = []

    if args.experiment in ("exp1", "all"):
        exp1_dir = results_dir / "experiment1"
        if exp1_dir.exists():
            print("Collecting Experiment 1 metrics...")
            rows = collect_experiment_metrics(exp1_dir)
            all_rows.extend(rows)

    if args.experiment in ("exp2", "all"):
        exp2_dir = results_dir / "experiment2"
        if exp2_dir.exists():
            print("Collecting Experiment 2 metrics...")
            rows = collect_experiment_metrics(exp2_dir)
            all_rows.extend(rows)

    if args.experiment in ("exp3", "all"):
        exp3_dir = results_dir / "experiment3"
        if exp3_dir.exists():
            print("Collecting Experiment 3 metrics...")
            rows = collect_experiment_metrics(exp3_dir)
            all_rows.extend(rows)

    if args.experiment in ("exp4", "all"):
        exp4_dir = results_dir / "experiment4"
        if exp4_dir.exists():
            print("Collecting Experiment 4 metrics...")
            rows = collect_experiment_metrics(exp4_dir)
            all_rows.extend(rows)

    if not all_rows:
        print("No metrics found. Ensure workflows have been run first.")
        sys.exit(0)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(all_rows, output_path)


if __name__ == "__main__":
    main()

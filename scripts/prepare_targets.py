#!/usr/bin/env python3
"""
Prepare target proteins for folding model comparison experiments.

Downloads experimental structures from RCSB PDB and extracts chain-specific
FASTA sequences and cleaned PDB files for use as ground truth references.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import urlretrieve, urlopen
from urllib.error import URLError

import yaml


RCSB_PDB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
RCSB_CIF_URL = "https://files.rcsb.org/download/{pdb_id}.cif"
RCSB_FASTA_URL = "https://www.rcsb.org/fasta/entry/{pdb_id}/display"


def load_targets(config_path: str) -> list[dict]:
    """Load target definitions from YAML config."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["targets"]


def download_pdb(pdb_id: str, output_dir: Path, fmt: str = "pdb") -> Path:
    """Download experimental structure from RCSB."""
    pdb_id_lower = pdb_id.lower()
    if fmt == "cif":
        url = RCSB_CIF_URL.format(pdb_id=pdb_id_lower)
        outfile = output_dir / f"{pdb_id_lower}.cif"
    else:
        url = RCSB_PDB_URL.format(pdb_id=pdb_id_lower)
        outfile = output_dir / f"{pdb_id_lower}.pdb"

    if outfile.exists():
        print(f"  [skip] {outfile.name} already exists")
        return outfile

    print(f"  Downloading {url}")
    try:
        urlretrieve(url, outfile)
    except URLError as e:
        print(f"  [ERROR] Failed to download {pdb_id}: {e}", file=sys.stderr)
        return None
    return outfile


def extract_chain_pdb(pdb_path: Path, chain_id: str, output_path: Path) -> Path:
    """Extract a single chain from a PDB file."""
    lines = []
    with open(pdb_path) as f:
        for line in f:
            if line.startswith(("ATOM", "HETATM")):
                if len(line) > 21 and line[21] == chain_id:
                    lines.append(line)
            elif line.startswith("END"):
                lines.append(line)

    if not lines:
        print(f"  [WARN] No atoms found for chain {chain_id} in {pdb_path.name}")
        return None

    with open(output_path, "w") as f:
        f.writelines(lines)
        if not any(l.startswith("END") for l in lines):
            f.write("END\n")

    return output_path


def extract_sequence_from_pdb(pdb_path: Path, chain_id: str) -> str:
    """Extract amino acid sequence from ATOM records of a PDB chain."""
    three_to_one = {
        "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
        "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
        "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
        "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
        "SEC": "U", "PYL": "O",
    }

    residues = {}
    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") and len(line) > 21 and line[21] == chain_id:
                resname = line[17:20].strip()
                resnum = int(line[22:26].strip())
                if resname in three_to_one and resnum not in residues:
                    residues[resnum] = three_to_one[resname]

    if not residues:
        return ""

    # Build sequence in residue number order
    seq = "".join(residues[k] for k in sorted(residues.keys()))
    return seq


def write_fasta(sequence: str, header: str, output_path: Path):
    """Write a single-sequence FASTA file."""
    with open(output_path, "w") as f:
        f.write(f">{header}\n")
        # Wrap at 80 characters
        for i in range(0, len(sequence), 80):
            f.write(sequence[i : i + 80] + "\n")


def write_boltz_yaml(sequence: str, name: str, output_path: Path, msa_path: str = None):
    """Write a Boltz-compatible YAML input file."""
    entry = {
        "sequences": [
            {
                "id": "A",
                "entity_type": "protein",
                "sequence": sequence,
            }
        ]
    }
    if msa_path:
        entry["sequences"][0]["msa"] = msa_path

    with open(output_path, "w") as f:
        yaml.dump(entry, f, default_flow_style=False)


def prepare_target(target: dict, exp_dir: Path, data_dir: Path) -> dict:
    """Prepare a single target: download PDB, extract chain, write FASTA and Boltz YAML."""
    pdb_id = target["pdb_id"]
    chain = target["chain"]
    name = target.get("name", pdb_id)

    print(f"\nProcessing {pdb_id} chain {chain} ({name})...")

    # Download full PDB
    full_pdb = download_pdb(pdb_id, exp_dir)
    if full_pdb is None:
        return None

    # Extract chain
    chain_pdb = exp_dir / f"{pdb_id.lower()}_chain{chain}.pdb"
    result = extract_chain_pdb(full_pdb, chain, chain_pdb)
    if result is None:
        return None

    # Extract sequence
    sequence = extract_sequence_from_pdb(full_pdb, chain)
    if not sequence:
        print(f"  [WARN] Could not extract sequence for {pdb_id} chain {chain}")
        return None

    print(f"  Sequence length: {len(sequence)}")

    # Write FASTA
    fasta_path = data_dir / f"{pdb_id.lower()}_chain{chain}.fasta"
    write_fasta(sequence, f"{pdb_id}_{chain} | {name}", fasta_path)

    # Write Boltz YAML (without MSA — to be added later)
    boltz_yaml = data_dir / f"{pdb_id.lower()}_chain{chain}.boltz.yaml"
    write_boltz_yaml(sequence, f"{pdb_id}_{chain}", boltz_yaml)

    return {
        "pdb_id": pdb_id,
        "chain": chain,
        "name": name,
        "sequence": sequence,
        "sequence_length": len(sequence),
        "experimental_pdb": str(chain_pdb),
        "fasta": str(fasta_path),
        "boltz_yaml": str(boltz_yaml),
        "category": target.get("category", "unknown"),
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare protein targets for folding experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/targets_pilot.yaml",
        help="Path to target configuration YAML",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Base data directory",
    )
    parser.add_argument(
        "--output-manifest",
        type=str,
        default="data/targets.json",
        help="Output manifest JSON with prepared target metadata",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    exp_dir = data_dir / "experimental"
    exp_dir.mkdir(parents=True, exist_ok=True)

    targets = load_targets(args.config)
    print(f"Loaded {len(targets)} targets from {args.config}")

    manifest = []
    for target in targets:
        result = prepare_target(target, exp_dir, data_dir)
        if result:
            manifest.append(result)

    # Write manifest
    manifest_path = Path(args.output_manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Prepared {len(manifest)}/{len(targets)} targets")
    print(f"Manifest written to {manifest_path}")
    print(f"Experimental PDBs in {exp_dir}")


if __name__ == "__main__":
    main()

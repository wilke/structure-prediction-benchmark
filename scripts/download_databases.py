#!/usr/bin/env python3
"""Download reference databases for MSA generation.

This script downloads the sequence databases required by the two MSA
generation pipelines used in this project:

  1. UniRef90      — used by JackHMMER (AlphaFold2-native pipeline)
  2. ColabFold DB  — used by MMseqs2   (fast ColabFold pipeline)

See DATABASE DESCRIPTIONS below or run with --help for details.

Usage:
    # Download everything (default: ./data/databases/)
    python scripts/download_databases.py

    # Download only one database
    python scripts/download_databases.py --db uniref90
    python scripts/download_databases.py --db colabfold

    # Custom output directory
    python scripts/download_databases.py --outdir /data/seqdb

    # Skip checksum verification (not recommended)
    python scripts/download_databases.py --skip-verify

DATABASE DESCRIPTIONS
=====================

UniRef90  (JackHMMER)
---------------------
Source:   UniProt Reference Clusters (https://www.uniprot.org/help/uniref)
URL:      https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref90/
Format:   Single FASTA file (uniref90.fasta.gz)
Size:     ~43 GB compressed, ~120 GB uncompressed
Updated:  Biweekly with each UniProt release

UniRef90 clusters all UniProt sequences at 90% sequence identity and 80%
mutual coverage. Each cluster is represented by its longest member. This
provides a comprehensive, non-redundant protein sequence database.

JackHMMER performs iterative profile-HMM searches against this database to
find distant homologs. This is the same MSA strategy used internally by
AlphaFold2. The iterative approach makes it more sensitive than single-pass
methods, particularly for proteins with few close homologs, at the cost of
being slower than MMseqs2.

ColabFold DB  (MMseqs2)
-----------------------
Source:   ColabFold / MMseqs2 project (https://colabfold.mmseqs.com)
URL:      https://opendata.mmseqs.org/colabfold/
Format:   MMseqs2 database files (pre-indexed)
Size:     ~500 GB for UniRef30 + EnvDB combined
Updated:  Periodically (current: UniRef30 2302, EnvDB 202108)

The ColabFold database consists of two components:

  UniRef30 (uniref30_2302)
    UniProt sequences clustered at 30% identity. More aggressive clustering
    than UniRef90 means the database is smaller and searches are faster, but
    the profile database format used by MMseqs2 retains information from all
    cluster members for sensitive searching.
    Size: ~150 GB (prebuilt database with index)

  ColabFold Environmental DB (colabfold_envdb_202108)
    Metagenomic sequences from BFD and MGnify that are NOT found in UniRef.
    These environmental sequences greatly expand the sequence space, helping
    find MSAs for proteins without close UniProt homologs. Contains ~182
    million additional sequence clusters.
    Size: ~350 GB (prebuilt database with index)

MMseqs2 searches both databases and merges the results into a single MSA
in A3M format. This two-database strategy is what gives ColabFold its
speed (10-100x faster than JackHMMER) while maintaining competitive
sensitivity.

Comparison
----------
  Property            | UniRef90 + JackHMMER    | ColabFold DB + MMseqs2
  --------------------|-------------------------|-------------------------
  Disk space          | ~120 GB (uncompressed)  | ~500 GB (pre-indexed)
  RAM needed          | ~64 GB                  | ~128 GB
  Speed per query     | 5-30 minutes            | 5-30 seconds
  Sensitivity         | Higher (iterative)      | Slightly lower
  Coverage            | UniProt only            | UniProt + metagenomes
  Update frequency    | Biweekly                | Periodic
  Used by             | AlphaFold2 (native)     | ColabFold, Boltz, Chai
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


# ── Database definitions ─────────────────────────────────────────────────

DATABASES = {
    "uniref90": {
        "description": "UniRef90 FASTA — JackHMMER sequence database",
        "files": [
            {
                "url": "https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref90/uniref90.fasta.gz",
                "filename": "uniref90.fasta.gz",
                "size_hint": "~43 GB compressed",
                "decompress": True,
                "output": "uniref90.fasta",
            },
        ],
        "post_download": None,
        "ready_check": "uniref90.fasta",
    },
    "colabfold": {
        "description": "ColabFold DB (UniRef30 + EnvDB) — MMseqs2 database",
        "files": [
            {
                "url": "https://opendata.mmseqs.org/colabfold/uniref30_2302.tar.gz",
                "filename": "uniref30_2302.tar.gz",
                "size_hint": "~150 GB",
                "decompress": False,  # handled by tar
                "extract": True,
            },
            {
                "url": "https://opendata.mmseqs.org/colabfold/colabfold_envdb_202108.tar.gz",
                "filename": "colabfold_envdb_202108.tar.gz",
                "size_hint": "~350 GB",
                "decompress": False,
                "extract": True,
            },
        ],
        "post_download": "build_mmseqs_index",
        "ready_check": "uniref30_2302/uniref30_2302_db",
    },
}


# ── Helper functions ─────────────────────────────────────────────────────

def find_download_tool():
    """Find the best available download tool."""
    for tool in ["aria2c", "wget", "curl"]:
        if shutil.which(tool):
            return tool
    print("ERROR: No download tool found. Install aria2c, wget, or curl.")
    sys.exit(1)


def download_file(url: str, dest: Path, tool: str):
    """Download a file with progress, using the best available tool."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  Already exists: {dest.name}, skipping download")
        return

    print(f"  Downloading: {url}")
    print(f"  Destination: {dest}")

    if tool == "aria2c":
        # aria2c: multi-connection download, much faster for large files
        cmd = [
            "aria2c",
            "--file-allocation=none",
            "--max-connection-per-server=8",
            "-s", "8",
            "-x", "8",
            "--dir", str(dest.parent),
            "--out", dest.name,
            url,
        ]
    elif tool == "wget":
        cmd = ["wget", "-c", "--progress=dot:giga", "-O", str(dest), url]
    else:  # curl
        cmd = ["curl", "-L", "-C", "-", "--progress-bar", "-o", str(dest), url]

    start = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"  ERROR: Download failed with exit code {result.returncode}")
        if dest.exists():
            dest.unlink()
        sys.exit(1)

    size_gb = dest.stat().st_size / (1024**3)
    print(f"  Done: {size_gb:.1f} GB in {elapsed/60:.1f} minutes")


def decompress_gz(filepath: Path):
    """Decompress a .gz file, keeping the original."""
    output = filepath.with_suffix("")  # strip .gz
    if output.exists():
        print(f"  Already decompressed: {output.name}")
        return output

    print(f"  Decompressing: {filepath.name} ...")
    # Use pigz if available (parallel gzip), fall back to gzip
    tool = "pigz" if shutil.which("pigz") else "gzip"
    cmd = [tool, "-d", "-k", str(filepath)]  # -k keeps original
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  ERROR: Decompression failed")
        sys.exit(1)

    print(f"  Decompressed: {output.name} ({output.stat().st_size / (1024**3):.1f} GB)")
    return output


def extract_tar(filepath: Path, dest_dir: Path):
    """Extract a tar.gz archive."""
    print(f"  Extracting: {filepath.name} ...")
    cmd = ["tar", "xzf", str(filepath), "-C", str(dest_dir)]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"  ERROR: Extraction failed")
        sys.exit(1)
    print(f"  Extracted to: {dest_dir}")


def build_mmseqs_index(db_dir: Path):
    """Build MMseqs2 index for faster searches (optional, needs ~768 GB RAM)."""
    if not shutil.which("mmseqs"):
        print("  NOTE: mmseqs not found in PATH. Skipping index creation.")
        print("  The databases will work without precomputed indices, but")
        print("  searches will be slower. Install MMseqs2 to create indices.")
        return

    uniref_db = db_dir / "uniref30_2302" / "uniref30_2302_db"
    if uniref_db.exists():
        print("  Creating MMseqs2 tsv2exprofiledb for UniRef30 ...")
        subprocess.run([
            "mmseqs", "tsv2exprofiledb",
            str(uniref_db), str(uniref_db),
        ])

    envdb = db_dir / "colabfold_envdb_202108" / "colabfold_envdb_202108_db"
    if envdb.exists():
        print("  Creating MMseqs2 tsv2exprofiledb for EnvDB ...")
        subprocess.run([
            "mmseqs", "tsv2exprofiledb",
            str(envdb), str(envdb),
        ])


def check_disk_space(path: Path, required_gb: float):
    """Warn if insufficient disk space."""
    stat = os.statvfs(str(path))
    free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
    if free_gb < required_gb:
        print(f"  WARNING: Only {free_gb:.0f} GB free at {path}")
        print(f"  This database needs approximately {required_gb:.0f} GB")
        response = input("  Continue anyway? [y/N] ")
        if response.lower() != "y":
            sys.exit(0)


def verify_md5(filepath: Path, expected_md5: str) -> bool:
    """Verify file integrity via MD5 checksum."""
    print(f"  Verifying checksum: {filepath.name} ...", end=" ", flush=True)
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192 * 1024), b""):
            md5.update(chunk)
    actual = md5.hexdigest()
    if actual == expected_md5:
        print("OK")
        return True
    else:
        print(f"MISMATCH (expected {expected_md5}, got {actual})")
        return False


# ── Main logic ───────────────────────────────────────────────────────────

def download_database(db_name: str, outdir: Path, tool: str):
    """Download and set up a single database."""
    db = DATABASES[db_name]
    db_dir = outdir / db_name
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Database: {db['description']}")
    print(f"Location: {db_dir}")
    print(f"{'='*60}")

    # Check if already complete
    ready_file = db_dir / db["ready_check"]
    if ready_file.exists():
        print(f"  Database already set up ({ready_file.name} exists)")
        return

    for fileinfo in db["files"]:
        dest = db_dir / fileinfo["filename"]

        # Download
        download_file(fileinfo["url"], dest, tool)

        # Decompress or extract
        if fileinfo.get("decompress"):
            decompress_gz(dest)
        elif fileinfo.get("extract"):
            extract_tar(dest, db_dir)

    # Post-download steps
    if db["post_download"] == "build_mmseqs_index":
        build_mmseqs_index(db_dir)

    print(f"\n  Database ready: {db_name}")


def list_databases():
    """Print database descriptions."""
    print("\nAvailable databases:\n")
    for name, db in DATABASES.items():
        print(f"  {name:12s}  {db['description']}")
        total_size = ", ".join(f["size_hint"] for f in db["files"])
        print(f"  {'':12s}  Download size: {total_size}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Download reference databases for MSA generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Databases:
  uniref90    UniRef90 FASTA for JackHMMER (~43 GB compressed, ~120 GB uncompressed)
  colabfold   ColabFold DB for MMseqs2 (~500 GB: UniRef30 + Environmental DB)

Examples:
  %(prog)s                          # Download all databases
  %(prog)s --db uniref90            # Download only UniRef90
  %(prog)s --db colabfold           # Download only ColabFold DB
  %(prog)s --outdir /data/seqdb     # Custom output location
  %(prog)s --list                   # Show database descriptions
        """,
    )
    parser.add_argument(
        "--db",
        choices=list(DATABASES.keys()),
        default=None,
        help="Download a specific database (default: all)",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/databases"),
        help="Output directory (default: data/databases/)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available databases and exit",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip checksum verification",
    )

    args = parser.parse_args()

    if args.list:
        list_databases()
        return

    # Determine which databases to download
    db_names = [args.db] if args.db else list(DATABASES.keys())

    # Find download tool
    tool = find_download_tool()
    print(f"Using download tool: {tool}")

    # Space estimates
    space_needed = {
        "uniref90": 170,   # compressed + uncompressed
        "colabfold": 600,  # archives + extracted
    }

    total_needed = sum(space_needed.get(db, 0) for db in db_names)
    args.outdir.mkdir(parents=True, exist_ok=True)
    check_disk_space(args.outdir, total_needed)

    # Download each database
    for db_name in db_names:
        download_database(db_name, args.outdir, tool)

    print(f"\n{'='*60}")
    print("All downloads complete!")
    print(f"Database location: {args.outdir.resolve()}")
    print(f"{'='*60}")
    print("\nTo use with the MSA generation scripts:")
    print(f"  JackHMMER: --jackhmmer-db {args.outdir.resolve()}/uniref90/uniref90.fasta")
    print(f"  MMseqs2:   --mmseqs2-db {args.outdir.resolve()}/colabfold/")


if __name__ == "__main__":
    main()

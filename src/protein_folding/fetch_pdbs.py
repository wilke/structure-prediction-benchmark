#!/usr/bin/env python3
"""
Fetch 100 experimentally verified PDB structures and their protein sequences
from the RCSB Protein Data Bank.
"""

import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Determine project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Default configuration
DEFAULT_NUM_PDBS = 140  # Request more to account for unreleased entries
DEFAULT_PDB_DIR = DATA_DIR / "pdbs"
DEFAULT_FASTA_DIR = DATA_DIR / "sequences"
DEFAULT_SUMMARY_FILE = DATA_DIR / "pdb_summary.tsv"

# RCSB PDB API endpoints
SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
PDB_DOWNLOAD_URL = "https://files.rcsb.org/download/{}.pdb"
FASTA_DOWNLOAD_URL = "https://www.rcsb.org/fasta/entry/{}"
ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/{}"


def search_experimental_pdbs(limit: int = 100) -> list[str]:
    """
    Search for experimentally verified protein structures.
    Returns a list of PDB IDs.
    """
    query = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "exptl.method",
                        "operator": "exact_match",
                        "value": "X-RAY DIFFRACTION"
                    }
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "entity_poly.rcsb_entity_polymer_type",
                        "operator": "exact_match",
                        "value": "Protein"
                    }
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entry_info.resolution_combined",
                        "operator": "less",
                        "value": 2.5
                    }
                }
            ]
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {
                "start": 0,
                "rows": limit
            },
            "sort": [
                {
                    "sort_by": "rcsb_accession_info.deposit_date",
                    "direction": "desc"
                }
            ]
        }
    }

    print(f"Searching for {limit} experimentally verified PDB structures...")
    response = requests.post(SEARCH_URL, json=query)
    response.raise_for_status()

    results = response.json()
    pdb_ids = [hit["identifier"] for hit in results.get("result_set", [])]
    print(f"Found {len(pdb_ids)} PDB entries")
    return pdb_ids


def get_entry_info(pdb_id: str) -> dict:
    """Get metadata for a PDB entry."""
    try:
        response = requests.get(ENTRY_URL.format(pdb_id))
        response.raise_for_status()
        data = response.json()
        return {
            "pdb_id": pdb_id,
            "title": data.get("struct", {}).get("title", "N/A"),
            "method": data.get("exptl", [{}])[0].get("method", "N/A"),
            "resolution": data.get("rcsb_entry_info", {}).get("resolution_combined", ["N/A"])[0],
            "deposit_date": data.get("rcsb_accession_info", {}).get("deposit_date", "N/A"),
            "organism": data.get("rcsb_entry_container_identifiers", {}).get("entry_id", "N/A")
        }
    except Exception as e:
        return {"pdb_id": pdb_id, "error": str(e)}


def download_pdb(pdb_id: str, output_dir: Path) -> bool:
    """Download a PDB file."""
    output_file = output_dir / f"{pdb_id}.pdb"
    if output_file.exists():
        return True

    try:
        url = PDB_DOWNLOAD_URL.format(pdb_id)
        response = requests.get(url)
        response.raise_for_status()
        output_file.write_text(response.text)
        return True
    except Exception as e:
        print(f"Error downloading {pdb_id}: {e}")
        return False


def download_fasta(pdb_id: str, output_dir: Path) -> bool:
    """Download FASTA sequence for a PDB entry."""
    output_file = output_dir / f"{pdb_id}.fasta"
    if output_file.exists():
        return True

    try:
        url = FASTA_DOWNLOAD_URL.format(pdb_id)
        response = requests.get(url)
        response.raise_for_status()
        output_file.write_text(response.text)
        return True
    except Exception as e:
        print(f"Error downloading FASTA for {pdb_id}: {e}")
        return False


def download_entry(pdb_id: str, pdb_dir: Path, fasta_dir: Path) -> tuple[str, bool, bool]:
    """Download both PDB and FASTA for an entry."""
    pdb_ok = download_pdb(pdb_id, pdb_dir)
    fasta_ok = download_fasta(pdb_id, fasta_dir)
    return pdb_id, pdb_ok, fasta_ok


def main():
    parser = argparse.ArgumentParser(
        description="Fetch experimentally verified PDB structures and sequences"
    )
    parser.add_argument(
        "-n", "--num-pdbs",
        type=int,
        default=DEFAULT_NUM_PDBS,
        help=f"Number of PDBs to request (default: {DEFAULT_NUM_PDBS})"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=DATA_DIR,
        help=f"Output directory for data (default: {DATA_DIR})"
    )
    args = parser.parse_args()

    # Set up paths
    pdb_dir = args.output_dir / "pdbs"
    fasta_dir = args.output_dir / "sequences"
    summary_file = args.output_dir / "pdb_summary.tsv"

    # Create output directories
    pdb_dir.mkdir(parents=True, exist_ok=True)
    fasta_dir.mkdir(parents=True, exist_ok=True)

    # Search for PDB IDs
    pdb_ids = search_experimental_pdbs(args.num_pdbs)

    if not pdb_ids:
        print("No PDB entries found!")
        return

    # Download PDBs and sequences in parallel
    print(f"\nDownloading {len(pdb_ids)} PDB structures and sequences...")
    successful = []
    failed = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(download_entry, pdb_id, pdb_dir, fasta_dir): pdb_id
            for pdb_id in pdb_ids
        }

        for i, future in enumerate(as_completed(futures), 1):
            pdb_id, pdb_ok, fasta_ok = future.result()
            status = "✓" if (pdb_ok and fasta_ok) else "✗"
            print(f"[{i}/{len(pdb_ids)}] {pdb_id}: {status}")

            if pdb_ok and fasta_ok:
                successful.append(pdb_id)
            else:
                failed.append(pdb_id)

    # Get metadata for successful downloads
    print("\nFetching metadata for downloaded structures...")
    metadata = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_entry_info, pdb_id): pdb_id for pdb_id in successful}
        for future in as_completed(futures):
            info = future.result()
            metadata.append(info)

    # Write summary file
    with open(summary_file, "w") as f:
        f.write("PDB_ID\tTitle\tMethod\tResolution\tDeposit_Date\n")
        for entry in sorted(metadata, key=lambda x: x.get("pdb_id", "")):
            if "error" not in entry:
                f.write(f"{entry['pdb_id']}\t{entry['title']}\t{entry['method']}\t{entry['resolution']}\t{entry['deposit_date']}\n")

    # Print summary
    print(f"\n{'='*60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Total requested:     {args.num_pdbs}")
    print(f"Successfully downloaded: {len(successful)}")
    print(f"Failed:              {len(failed)}")
    print(f"\nPDB files saved to:  {pdb_dir}/")
    print(f"FASTA files saved to: {fasta_dir}/")
    print(f"Summary saved to:    {summary_file}")

    if failed:
        print(f"\nFailed PDB IDs: {', '.join(failed)}")


if __name__ == "__main__":
    main()

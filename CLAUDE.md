# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a computational framework for comparing protein structure prediction tools (AlphaFold2, Boltz, Chai, ESMFold) with and without Multiple Sequence Alignments (MSA), benchmarked against experimentally verified PDB structures.

## Commands

### Setup and Dependencies
```bash
pip install -e .                    # Install package in dev mode
pip install -e ".[dev]"             # Include dev dependencies (pytest, ruff)
pip install pyyaml matplotlib seaborn pandas numpy  # Additional analysis deps
```

### Linting and Testing
```bash
ruff check .                        # Lint code
ruff check --fix .                  # Auto-fix lint issues
pytest                              # Run tests
pytest tests/test_file.py::test_fn  # Run single test
```

### Data Preparation
```bash
fetch-pdbs -n 100                   # Download PDBs from RCSB (installed entrypoint)
python scripts/prepare_targets.py --config configs/targets_pilot.yaml
python scripts/generate_msas.py --config configs/targets_pilot.yaml \
  --jackhmmer-db /path/to/uniref90.fasta --mmseqs2-db /path/to/colabfold_db
```

### Running Experiments (via GoWe)
```bash
gowe submit cwl/workflows/experiment1-within-tool.cwl \
  --input target_fastas=data/*.fasta \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb
gowe status <submission_id>
```

### Analyzing Results
```bash
python scripts/collect_metrics.py --results-dir results/
python scripts/plot_results.py --metrics results/all_metrics.csv
```

## Architecture

### Core Components

**CWL Workflows** (`cwl/workflows/`): Four experiments comparing prediction accuracy:
- `experiment1-within-tool.cwl`: Per-tool baseline accuracy vs experimental structures
- `experiment2-across-tools.cwl`: Cross-tool pairwise structure comparison
- `experiment3-msa-impact.cwl`: MSA vs no-MSA prediction quality
- `experiment4-msa-depth.cwl`: Quality vs MSA depth (1 to 1024 sequences)

**CWL Tools** (`cwl/tools/`): CommandLineTool wrappers for Docker containers:
- Prediction: `alphafold-predict.cwl`, `boltz-predict.cwl`, `chai-predict.cwl`, `esmfold-predict.cwl`
- MSA generation: `mmseqs2-msa.cwl`, `jackhmmer-msa.cwl`, `subsample-msa.cwl`
- Comparison: `compare-structures.cwl` (wraps protein_structure_analysis)

**Scripts** (`scripts/`): Python utilities for orchestration:
- `prepare_targets.py`: Downloads PDBs, extracts chains, generates FASTA files
- `generate_msas.py`: Orchestrates MMseqs2 and JackHMMER MSA generation
- `collect_metrics.py`: Aggregates JSON metrics from workflow outputs into CSV
- `subsample_msa.py`: Creates MSAs at various depths for experiment 4

### Data Flow

1. Target config (`configs/targets_pilot.yaml`) defines PDB IDs and chains
2. `prepare_targets.py` downloads experimental structures → `data/experimental/`
3. `generate_msas.py` creates MSAs → `data/msas/{mmseqs2,jackhmmer}/`
4. CWL workflows run predictions via GoWe → `results/`
5. `collect_metrics.py` aggregates comparison metrics → `results/all_metrics.csv`

### Key Metrics

Structure comparisons use the `protein_structure_analysis` toolkit:
- TM-score (>0.5 = same fold), RMSD, GDT-TS, GDT-HA, contact Jaccard, SS agreement

## External Dependencies

- **GoWe**: CWL workflow engine for submitting/tracking experiments
- **Docker images**: `wilke/alphafold`, `dxkb/boltz`, `dxkb/chai`, `dxkb/esmfold`
- **protein_structure_analysis**: Structure comparison toolkit (TM-score, RMSD)
- **Sequence databases**: UniRef90 (JackHMMER), ColabFold DB (MMseqs2)

# Protein Folding Model Comparison: MSA Impact Study

A systematic computational experiment framework comparing protein structure prediction tools with and without Multiple Sequence Alignments (MSA), benchmarked against experimentally verified structures.

## Tools Under Test

| Tool | Docker Image | MSA Support | No-MSA Mode |
|------|-------------|-------------|-------------|
| AlphaFold2 | `wilke/alphafold` | Yes (JackHMMER+HHblits) | Single-seq A3M* |
| Boltz | `dxkb/boltz` | Yes (precomputed A3M or server) | Yes |
| Chai | `dxkb/chai` | Yes (precomputed A3M) | Yes |
| ESMFold | `dxkb/esmfold` | No (single-sequence only) | Always |

*AlphaFold2 requires MSA input; for "no-MSA" testing we provide a single-sequence A3M.

## Experiments

### Experiment 1: Within-Tool Quality Assessment
Predicts structures with each tool using default settings and compares against experimental PDB structures. Establishes baseline per-tool accuracy.

**Workflow:** `cwl/workflows/experiment1-within-tool.cwl`

### Experiment 2: Cross-Tool Comparison
All-vs-all pairwise structural comparison of predictions from different tools for the same targets. Reveals agreement and divergence patterns between methods.

**Workflow:** `cwl/workflows/experiment2-across-tools.cwl`

### Experiment 3: MSA Impact
Quantifies how MSA affects prediction quality by running each tool in both MSA and no-MSA modes. Also compares MSA generation methods (MMseqs2 vs JackHMMER).

**Conditions:** no_msa, msa_mmseqs2, msa_jackhmmer

**Workflow:** `cwl/workflows/experiment3-msa-impact.cwl`

### Experiment 4: MSA Depth Sensitivity
Subsamples MSAs to varying depths (1, 8, 16, 32, 64, 128, 256, 512, 1024, full) and measures prediction quality at each level. Determines optimal MSA size and how MSA source influences the depth–quality relationship.

**Workflow:** `cwl/workflows/experiment4-msa-depth.cwl`

## Metrics

All comparisons use the [protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) toolkit:

| Metric | Interpretation |
|--------|---------------|
| TM-score | Global fold similarity (0–1; >0.5 = same fold) |
| RMSD | Backbone deviation in Ångströms |
| Weighted RMSD | pLDDT-weighted deviation |
| GDT-TS | Fraction of residues within 1/2/4/8 Å |
| GDT-HA | High-accuracy variant (0.5/1/2/4 Å) |
| Contact Jaccard | Contact map similarity |
| SS Agreement | Secondary structure match fraction |

## Project Structure

```
├── configs/
│   └── targets_pilot.yaml         # 10 pilot proteins (diverse fold classes)
├── cwl/
│   ├── tools/                     # CWL CommandLineTool definitions
│   │   ├── alphafold-predict.cwl
│   │   ├── boltz-predict.cwl
│   │   ├── chai-predict.cwl
│   │   ├── esmfold-predict.cwl
│   │   ├── compare-structures.cwl
│   │   ├── batch-compare.cwl
│   │   ├── mmseqs2-msa.cwl
│   │   ├── jackhmmer-msa.cwl
│   │   ├── subsample-msa.cwl
│   │   ├── fetch-pdb.cwl
│   │   └── sto-to-a3m.cwl
│   └── workflows/                 # CWL Workflow definitions
│       ├── experiment1-within-tool.cwl
│       ├── experiment2-across-tools.cwl
│       ├── experiment3-msa-impact.cwl
│       └── experiment4-msa-depth.cwl
├── scripts/
│   ├── prepare_targets.py         # Download PDBs, extract sequences
│   ├── generate_msas.py           # Orchestrate MSA generation
│   ├── subsample_msa.py           # MSA depth subsampling
│   ├── collect_metrics.py         # Aggregate results into CSV
│   └── plot_results.py            # Generate comparison plots
├── data/
│   ├── targets.csv                # Target metadata
│   ├── experimental/              # Experimental PDB structures
│   └── msas/                      # Precomputed MSAs
│       ├── mmseqs2/
│       ├── jackhmmer/
│       └── subsampled/
└── results/                       # Workflow outputs (gitignored)
```

## Quickstart

### 1. Prepare targets

```bash
pip install pyyaml
python scripts/prepare_targets.py --config configs/targets_pilot.yaml
```

### 2. Generate MSAs

```bash
python scripts/generate_msas.py \
  --config configs/targets_pilot.yaml \
  --jackhmmer-db /path/to/uniref90.fasta \
  --mmseqs2-db /path/to/colabfold_db
```

### 3. Run experiments via GoWe

```bash
# Submit Experiment 1
gowe submit cwl/workflows/experiment1-within-tool.cwl \
  --input target_fastas=data/*.fasta \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb

# Check status
gowe status <submission_id>

# Get results
gowe logs <submission_id>
```

### 4. Analyze results

```bash
python scripts/collect_metrics.py --results-dir results/
python scripts/plot_results.py --metrics results/all_metrics.csv
```

## Pilot Target Set

10 diverse proteins covering multiple fold classes and difficulty levels:

| PDB | Name | Residues | Category |
|-----|------|----------|----------|
| 1UBQ | Ubiquitin | 76 | Easy/small |
| 1L2Y | Trp-cage miniprotein | 20 | Easy/small |
| 1MBN | Myoglobin | 153 | Alpha |
| 1TEN | Tenascin FnIII | 89 | Beta |
| 1AKE | Adenylate kinase | 214 | Alpha/beta |
| 4LZT | Lysozyme | 129 | Enzyme |
| 2SRC | Src kinase | 452 | Multi-domain |
| 1BL8 | Galectin-1 | 135 | Beta |
| 7MRX | CASP14 target | 141 | Hard |
| 7S0B | CASP15 target | 197 | Hard |

## Dependencies

- [GoWe](https://github.com/wilke/GoWe) — CWL workflow engine
- [protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) — Structure comparison metrics
- Docker — For running prediction tools
- Python 3.10+ with: pyyaml, matplotlib, seaborn, pandas, numpy

## Requirements

```bash
pip install pyyaml matplotlib seaborn pandas numpy
```

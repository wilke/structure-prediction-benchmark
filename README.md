# Protein Folding Model Comparison: MSA Impact Study

A systematic computational experiment framework comparing protein structure prediction tools with and without Multiple Sequence Alignments (MSA), benchmarked against experimentally verified structures.

## Tools Under Test

| Tool | Docker Image | MSA Support | Minimal-MSA Mode |
|------|-------------|-------------|-------------------|
| AlphaFold2 | `wilke/alphafold` | Yes (JackHMMER+HHblits) | Reduced-MSA (single-seq A3M)* |
| Boltz | `dxkb/boltz` | Yes (precomputed A3M or server) | No MSA |
| Chai | `dxkb/chai` | Yes (precomputed A3M) | No MSA |
| ESMFold | `dxkb/esmfold` | No (single-sequence only) | True single-sequence |

*AlphaFold2 with depth=1 A3M still processes through the Evoformer — this is **not** equivalent to ESMFold's true single-sequence architecture. We label this "reduced-MSA" to avoid false equivalence.

## Experiments

### Experiment 1: Within-Tool Quality Assessment
Predicts structures with each tool using default settings and compares against experimental PDB structures. Establishes baseline per-tool accuracy.

**Workflow:** `cwl/workflows/experiment1-within-tool.cwl`

### Experiment 2: Cross-Tool Comparison
All-vs-all pairwise structural comparison of predictions from different tools for the same targets. Reveals agreement and divergence patterns between methods.

**Workflow:** `cwl/workflows/experiment2-across-tools.cwl`

### Experiment 3: MSA Impact
Quantifies how MSA affects prediction quality by running each tool with and without MSA. Also compares MSA generation methods (MMseqs2 vs JackHMMER) across all tools.

**Conditions:** reduced_msa/no_msa, msa_mmseqs2, msa_jackhmmer

**Workflow:** `cwl/workflows/experiment3-msa-impact.cwl`

### Experiment 4: MSA Depth Sensitivity
Subsamples MSAs to varying depths (1, 8, 16, 32, 64, 128, 256, 512, 1024, full) and measures prediction quality at each level. Uses both raw depth and Neff (effective sequences) as the independent variable.

**Workflow:** `cwl/workflows/experiment4-msa-depth.cwl`

## Metrics

All structural comparisons use the [protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) toolkit with TM-align for structural alignment, DSSP for secondary structure, and Cb 8A contacts (Ca for glycine):

| Metric | Interpretation |
|--------|---------------|
| TM-score | Global fold similarity (0-1; >0.5 = same fold) |
| RMSD | Backbone deviation in Angstroms |
| Weighted RMSD | pLDDT-weighted deviation |
| GDT-TS | Fraction of residues within 1/2/4/8 A |
| GDT-HA | High-accuracy variant (0.5/1/2/4 A) |
| Contact Jaccard | Contact map similarity |
| SS Agreement | Secondary structure match fraction |
| pLDDT metrics | High-conf fraction, stratified RMSD/TM-score, calibration |
| Neff | Effective MSA sequences (information content) |

Statistical analysis includes paired Wilcoxon signed-rank tests, bootstrap 95% CIs, and Cohen's d effect sizes.

## Documentation

| Document | Description |
|----------|-------------|
| [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) | Full experiment plan with glossary, detailed steps, metrics reference, and CASP-style scale-up notes |
| [CONTAINERS.md](CONTAINERS.md) | Docker container registry and build instructions |
| [CLAUDE.md](CLAUDE.md) | Developer guidance for Claude Code |
| [docs/ProteinFoldingExperiment.pptx](docs/ProteinFoldingExperiment.pptx) | Presentation slides explaining the experiments |

## Project Structure

```
├── configs/
│   └── targets_pilot.yaml          # 10 pilot proteins (diverse fold classes)
├── cwl/
│   ├── tools/                      # CWL CommandLineTool definitions (11 tools)
│   │   ├── alphafold-predict.cwl
│   │   ├── boltz-predict.cwl
│   │   ├── chai-predict.cwl
│   │   ├── esmfold-predict.cwl
│   │   ├── compare-structures.cwl
│   │   ├── batch-compare.cwl
│   │   ├── mmseqs2-msa.cwl         # staphb/mmseqs2
│   │   ├── jackhmmer-msa.cwl       # staphb/hmmer
│   │   ├── subsample-msa.cwl
│   │   ├── fetch-pdb.cwl
│   │   └── sto-to-a3m.cwl
│   └── workflows/                  # CWL Workflow definitions
│       ├── experiment1-within-tool.cwl
│       ├── experiment2-across-tools.cwl
│       ├── experiment3-msa-impact.cwl
│       └── experiment4-msa-depth.cwl
├── docker/
│   └── protein-compare/
│       └── Dockerfile              # protein_structure_analysis container
├── docs/
│   └── ProteinFoldingExperiment.pptx
├── scripts/
│   ├── prepare_targets.py          # Download PDBs, extract sequences
│   ├── generate_msas.py            # Orchestrate MSA generation
│   ├── subsample_msa.py            # MSA depth subsampling
│   ├── download_databases.py       # Download UniRef90 and ColabFold DB
│   ├── compute_msa_stats.py        # Compute Neff, identity, coverage
│   ├── collect_metrics.py          # Aggregate results into CSV
│   └── plot_results.py             # Generate plots and statistical tests
├── data/
│   ├── targets.csv
│   ├── experimental/               # Experimental PDB structures
│   ├── databases/                  # Sequence databases (gitignored)
│   └── msas/                       # Precomputed MSAs
│       ├── mmseqs2/
│       ├── jackhmmer/
│       └── subsampled/
└── results/                        # Workflow outputs (gitignored)
```

## Quickstart

### 1. Download reference databases

```bash
# Download UniRef90 (for JackHMMER) and/or ColabFold DB (for MMseqs2)
python scripts/download_databases.py --db uniref90
python scripts/download_databases.py --db colabfold
```

### 2. Prepare targets

```bash
pip install pyyaml
python scripts/prepare_targets.py --config configs/targets_pilot.yaml
```

### 3. Generate MSAs

```bash
python scripts/generate_msas.py \
  --config configs/targets_pilot.yaml \
  --jackhmmer-db data/databases/uniref90/uniref90.fasta \
  --mmseqs2-db data/databases/colabfold/

# Compute MSA quality stats (Neff, coverage)
python scripts/compute_msa_stats.py --msa-dir data/msas/ --output data/msa_stats.csv
```

### 4. Run experiments via GoWe

```bash
# Submit Experiment 1
gowe submit cwl/workflows/experiment1-within-tool.cwl \
  --input target_fastas=data/*.fasta \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb

# Check status
gowe status <submission_id>
```

### 5. Analyze results

```bash
python scripts/collect_metrics.py --results-dir results/ --msa-stats data/msa_stats.csv
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

## Container Status

See [CONTAINERS.md](CONTAINERS.md) for full details. Summary: 7 of 8 containers are available. Only `dxkb/protein-compare` needs to be built from the included [Dockerfile](docker/protein-compare/Dockerfile).

## Dependencies

- [GoWe](https://github.com/wilke/GoWe) — CWL workflow engine
- [protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) — Structure comparison metrics
- Docker — For running prediction tools
- Python 3.10+ with: pyyaml, matplotlib, seaborn, pandas, numpy, scipy

```bash
pip install pyyaml matplotlib seaborn pandas numpy scipy
```

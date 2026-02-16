# Experiment Plan: Protein Folding Model Comparison with MSA Impact Analysis

## Table of Contents

1. [Study Objectives](#1-study-objectives)
2. [Glossary of Terms](#2-glossary-of-terms)
3. [Input Data](#3-input-data)
4. [Prediction Tools](#4-prediction-tools)
5. [Experiment 1: Within-Tool Quality Assessment](#5-experiment-1-within-tool-quality-assessment)
6. [Experiment 2: Cross-Tool Comparison](#6-experiment-2-cross-tool-comparison)
7. [Experiment 3: MSA Impact Analysis](#7-experiment-3-msa-impact-analysis)
8. [Experiment 4: MSA Depth Sensitivity](#8-experiment-4-msa-depth-sensitivity)
9. [Metrics and Evaluation](#9-metrics-and-evaluation)
10. [Execution and Orchestration](#10-execution-and-orchestration)
11. [Analysis Pipeline](#11-analysis-pipeline)

---

## 1. Study Objectives

This study systematically evaluates how Multiple Sequence Alignments (MSA) influence the accuracy of modern protein structure prediction tools. The central questions are:

1. How does each tool perform relative to experimentally determined structures?
2. Where do tools agree and disagree in their predictions?
3. Does removing MSA information degrade prediction quality, and by how much?
4. What is the minimum MSA depth needed to achieve near-optimal accuracy?
5. How well do the tools' own confidence estimates (pLDDT) correlate with actual prediction accuracy?

---

## 2. Glossary of Terms

### Structural Biology

| Term | Definition |
|------|-----------|
| **Protein folding** | The physical process by which a polypeptide chain acquires its three-dimensional functional structure. |
| **PDB (Protein Data Bank)** | The global archive of experimentally determined 3D structures of biological macromolecules, hosted at rcsb.org. Each entry is identified by a 4-character alphanumeric code (e.g., 1UBQ). |
| **Chain** | A single polypeptide within a PDB entry. Multi-chain entries contain multiple proteins or copies; we extract individual chains for prediction. |
| **FASTA** | A text-based format for representing amino acid sequences. Each entry has a header line starting with `>` followed by sequence lines. |
| **Residue** | A single amino acid within a protein chain. |
| **Resolution** | A measure of the detail visible in an experimental structure, in Angstroms (Å). Lower is better; <2.0 Å is considered high resolution. |
| **NMR** | Nuclear Magnetic Resonance spectroscopy; an experimental method for determining protein structures in solution. Does not have a traditional resolution value. |
| **Fold class** | A classification of protein structure based on its dominant secondary structure content (all-alpha, all-beta, alpha/beta, etc.). |

### Multiple Sequence Alignments

| Term | Definition |
|------|-----------|
| **MSA (Multiple Sequence Alignment)** | An alignment of three or more biological sequences (proteins or nucleic acids) that identifies conserved regions across evolutionarily related sequences. MSAs provide co-evolutionary information that helps predict which residues are spatially close in the 3D structure. |
| **A3M format** | A compressed variant of FASTA alignment format used by HHsuite and many folding tools. Insertions relative to the query are in lowercase; deletions are implicit (no dash characters for query gaps). The first sequence is always the query. |
| **Stockholm format** | An MSA format used by HMMER and Pfam. Includes metadata annotations. JackHMMER outputs this format; it must be converted to A3M for most folding tools. |
| **MSA depth** | The number of homologous sequences in an alignment. Deeper MSAs provide more co-evolutionary signal but require more compute. |
| **Single-sequence (no-MSA)** | A degenerate MSA containing only the query sequence (depth = 1). Tests whether a tool can predict structure from sequence alone, without evolutionary information. |
| **MMseqs2** | An ultra-fast sequence search and clustering tool. We use it with the ColabFold database for rapid MSA generation. Produces A3M output directly. |
| **JackHMMER** | An iterative profile HMM search tool from the HMMER suite. More sensitive than single-pass methods; AlphaFold2 uses it natively with UniRef90. Outputs Stockholm format. |
| **ColabFold DB** | A precomputed database combining UniRef30 and environmental sequences, optimized for ColabFold/MMseqs2-based MSA generation. |
| **UniRef90** | A clustered version of UniProt where sequences sharing >=90% identity are grouped. Used as the search database for JackHMMER. |

### Structure Comparison Metrics

| Term | Definition |
|------|-----------|
| **TM-score** | Template Modeling score. A length-normalized measure of structural similarity ranging from 0 to 1. Scores >0.5 generally indicate the same fold; >0.7 indicates high structural similarity. Unlike RMSD, TM-score is length-independent. |
| **RMSD** | Root Mean Square Deviation. The average distance (in Angstroms) between equivalent backbone atoms after optimal superposition. Lower is better; <2 Å is excellent for medium-sized proteins. |
| **Weighted RMSD** | RMSD weighted by per-residue pLDDT confidence scores. Downweights contributions from low-confidence regions, providing a fairer comparison when flexible loops are poorly predicted. |
| **GDT-TS** | Global Distance Test - Total Score. The average fraction of residues within 1, 2, 4, and 8 Å of their experimental positions after superposition. Ranges from 0 to 100; the primary metric used in CASP evaluations. |
| **GDT-HA** | Global Distance Test - High Accuracy. Like GDT-TS but with tighter thresholds (0.5, 1, 2, 4 Å). More discriminating for high-quality predictions. |
| **Contact Jaccard** | The Jaccard similarity index between predicted and experimental residue-residue contact maps. A contact is defined as C-beta atoms within 8 Å. Measures how well the tool captures the overall contact topology. |
| **SS Agreement** | Secondary Structure Agreement. The fraction of residues where predicted and experimental secondary structure (helix, strand, coil) assignments match. Computed via DSSP. |

### Confidence Metrics

| Term | Definition |
|------|-----------|
| **pLDDT** | Predicted Local Distance Difference Test. A per-residue confidence score (0-100) produced by structure prediction tools, stored in the B-factor column of PDB output files. Thresholds: >90 = very high confidence, 70-90 = confident, 50-70 = low confidence, <50 = very low confidence / likely disordered. |
| **pLDDT high-confidence fraction** | The fraction of residues with pLDDT >= 70. A global measure of how confident the tool is in its overall prediction. |
| **pLDDT low-confidence fraction** | The fraction of residues with pLDDT < 50. Indicates the proportion of the structure the tool considers unreliable or disordered. |
| **High-confidence RMSD** | RMSD computed only over residues with pLDDT >= 70. Tests whether the tool is accurate in regions it considers reliable. |
| **High-confidence TM-score** | TM-score computed only over high-confidence residues. |
| **pLDDT-accuracy correlation** | Pearson correlation between per-residue pLDDT and 1/(per-residue distance error). Measures how well the tool's confidence calibrates with actual accuracy; higher is better. |

### Tools and Infrastructure

| Term | Definition |
|------|-----------|
| **CWL** | Common Workflow Language (v1.2). A specification for describing analysis workflows and tools in a portable, reproducible way. Each tool and workflow is defined in a `.cwl` YAML file. |
| **GoWe** | A Go-based CWL v1.2 workflow engine that supports local, Docker, and BV-BRC execution backends. Used to orchestrate all experiments in this study. |
| **Docker** | A containerization platform. Each prediction tool runs in its own Docker container to ensure reproducibility and isolation. |
| **BV-BRC** | The Bacterial and Viral Bioinformatics Resource Center. Hosts the `protein_structure_analysis` toolkit used for structure comparison. |
| **protein_compare** | The CLI tool from `protein_structure_analysis` that computes all structural comparison metrics (TM-score, RMSD, GDT-TS, etc.) between two PDB structures. |
| **goweHint** | A CWL extension field that tells GoWe which executor backend to use (e.g., `dockerPull` for Docker containers). |

---

## 3. Input Data

### 3.1 Pilot Target Set

We use 10 experimentally determined protein structures selected for diversity across fold classes, sizes, and prediction difficulty. All structures are from the RCSB PDB with resolution better than 2.0 Å (except the NMR structure).

| PDB ID | Chain | Protein Name | Category | Residues | Resolution (Å) | Fold Class |
|--------|-------|-------------|----------|----------|----------------|------------|
| 1UBQ | A | Ubiquitin | Easy/small | 76 | 1.80 | All-beta |
| 1L2Y | A | Trp-cage miniprotein | Easy/small | 20 | NMR | Mini-protein |
| 1MBN | A | Myoglobin | Alpha | 153 | 1.40 | All-alpha |
| 1TEN | A | Tenascin fibronectin III | Beta | 89 | 1.80 | All-beta |
| 1AKE | A | Adenylate kinase | Alpha/beta | 214 | 1.63 | Alpha-beta |
| 4LZT | A | Hen egg-white lysozyme | Enzyme | 129 | 0.94 | Alpha-beta |
| 2SRC | A | Src tyrosine kinase | Multi-domain | 452 | 1.50 | Multi-domain |
| 1BL8 | A | Galectin-1 | Beta | 135 | 1.70 | All-beta |
| 7MRX | B | CASP14 target (T1091) | Hard | 141 | 1.60 | Novel |
| 7S0B | A | CASP15 target | Hard | 197 | 1.85 | Novel |

**Target configuration file:** [`configs/targets_pilot.yaml`](configs/targets_pilot.yaml)

### 3.2 Selection Criteria

Targets were chosen to cover:
- **Size range**: 20 to 452 residues, spanning miniproteins to multi-domain complexes
- **Fold diversity**: All-alpha, all-beta, mixed alpha-beta, multi-domain, and novel folds
- **Difficulty spectrum**: Well-studied proteins (ubiquitin, lysozyme) through recent CASP targets with limited homology
- **Resolution quality**: All X-ray structures resolved at <2.0 Å for reliable ground truth

### 3.3 Data Preparation Steps

1. **Download experimental structures**: Fetch PDB files from RCSB for each target ID
2. **Extract chains**: Isolate the specified chain from each PDB entry
3. **Generate FASTA sequences**: Extract amino acid sequences for input to prediction tools
4. **Create Boltz YAML inputs**: Generate tool-specific input manifests for Boltz

**Script:** [`scripts/prepare_targets.py`](scripts/prepare_targets.py)

```bash
python scripts/prepare_targets.py --config configs/targets_pilot.yaml
```

**Outputs:**
- `data/experimental/{PDB_ID}_chain{X}.pdb` — Extracted experimental structures
- `data/{PDB_ID}.fasta` — FASTA sequence files
- `data/{PDB_ID}_boltz.yaml` — Boltz input manifests
- `data/targets.json` — Master metadata file

### 3.4 MSA Generation

MSAs are precomputed using two independent methods, allowing comparison of how MSA source affects prediction quality.

**Script:** [`scripts/generate_msas.py`](scripts/generate_msas.py)

```bash
python scripts/generate_msas.py \
  --config configs/targets_pilot.yaml \
  --jackhmmer-db /path/to/uniref90.fasta \
  --mmseqs2-db /path/to/colabfold_db
```

**MMseqs2 pipeline:**
- Database: ColabFold DB (UniRef30 + environmental sequences)
- Tool: [`cwl/tools/mmseqs2-msa.cwl`](cwl/tools/mmseqs2-msa.cwl)
- Output: `data/msas/mmseqs2/{PDB_ID}.a3m`

**JackHMMER pipeline:**
- Database: UniRef90
- Tool: [`cwl/tools/jackhmmer-msa.cwl`](cwl/tools/jackhmmer-msa.cwl)
- Intermediate: Stockholm format, converted via [`cwl/tools/sto-to-a3m.cwl`](cwl/tools/sto-to-a3m.cwl)
- Output: `data/msas/jackhmmer/{PDB_ID}.a3m`

### 3.5 MSA Subsampling (Experiment 4)

For depth sensitivity analysis, full MSAs are subsampled to controlled depths using two strategies:

**Script:** [`scripts/subsample_msa.py`](scripts/subsample_msa.py)
**CWL tool:** [`cwl/tools/subsample-msa.cwl`](cwl/tools/subsample-msa.cwl)

**Depths tested:** 1, 8, 16, 32, 64, 128, 256, 512, 1024, full

**Subsampling strategies:**
- **Random**: Uniformly random selection of sequences (fast, simple)
- **Diversity-weighted**: Selects sequences to maximize sequence diversity within the subsample, preserving informative co-evolutionary signal even at low depths

The query sequence is always preserved as the first entry.

**Output:** `data/msas/subsampled/{method}/{PDB_ID}_depth{N}.a3m`

### 3.6 File Formats Summary

| Format | Extension | Used By | Description |
|--------|-----------|---------|-------------|
| PDB | `.pdb` | All tools (output), protein_compare | Atomic coordinates with B-factor column storing pLDDT |
| FASTA | `.fasta` | AlphaFold2, Chai, ESMFold | Amino acid sequence |
| A3M | `.a3m` | AlphaFold2, Boltz, Chai | Multiple sequence alignment |
| Stockholm | `.sto` | JackHMMER (output) | MSA with annotations; converted to A3M |
| YAML | `.yaml` | Boltz | Tool-specific input manifest |
| mmCIF | `.cif` | Boltz (output) | Macromolecular structure format; converted to PDB for comparison |
| JSON | `.json` | protein_compare (output) | Per-comparison metric results |
| CSV | `.csv` | Analysis scripts | Aggregated metrics table |

---

## 4. Prediction Tools

### 4.1 Tool Overview

| Tool | Docker Image | Approach | MSA Input | No-MSA Strategy |
|------|-------------|----------|-----------|-----------------|
| AlphaFold2 | `wilke/alphafold` | Co-evolution + attention | Required (A3M) | Single-sequence A3M |
| Boltz | `dxkb/boltz` | Diffusion-based generation | Optional (A3M or server) | Omit `msa:` field |
| Chai | `dxkb/chai` | Hybrid attention | Optional (A3M) | Omit MSA input |
| ESMFold | `dxkb/esmfold` | Protein language model | Not supported | Always single-sequence |

### 4.2 AlphaFold2

**CWL tool:** [`cwl/tools/alphafold-predict.cwl`](cwl/tools/alphafold-predict.cwl)

AlphaFold2 uses a deep neural network that combines MSA-derived co-evolutionary features with structural attention modules. It natively requires MSA input; for no-MSA testing, we supply a single-sequence A3M file containing only the query.

**Key parameters:**
- `model_preset`: `monomer` (single chain predictions)
- `use_precomputed_msas`: `true` (use our precomputed A3M files rather than running the internal MSA pipeline)
- `data_dir`: Path to AlphaFold model weights and databases

**Inputs:** FASTA sequence + precomputed A3M + model weights directory
**Outputs:** PDB file with pLDDT in B-factor column

### 4.3 Boltz

**CWL tool:** [`cwl/tools/boltz-predict.cwl`](cwl/tools/boltz-predict.cwl)

Boltz uses a diffusion-based approach to generate protein structures. It accepts a YAML manifest that specifies the input sequence and optionally an MSA file path.

**Key parameters:**
- `recycling_steps`: 3 (iterative refinement cycles)
- `diffusion_samples`: 1 (number of structure samples to generate)
- `use_msa_server`: false (use precomputed MSAs, not live server)

**Inputs:** YAML manifest (references FASTA and optionally A3M)
**Outputs:** mmCIF file (converted to PDB for comparison)

### 4.4 Chai

**CWL tool:** [`cwl/tools/chai-predict.cwl`](cwl/tools/chai-predict.cwl)

Chai is a hybrid structure prediction tool supporting optional MSA input. When an MSA file is provided, it incorporates co-evolutionary features; without one, it operates in single-sequence mode.

**Key parameters:**
- `num_models`: 1 (number of predicted models)

**Inputs:** FASTA sequence + optional A3M file
**Outputs:** PDB file with pLDDT in B-factor column

### 4.5 ESMFold

**CWL tool:** [`cwl/tools/esmfold-predict.cwl`](cwl/tools/esmfold-predict.cwl)

ESMFold uses the ESM-2 protein language model to predict structures from single sequences. It does not accept MSA input and serves as the single-sequence baseline across all experiments.

**Key parameters:**
- `num_recycles`: 4 (number of recycling iterations)

**Inputs:** FASTA sequence only
**Outputs:** PDB file with pLDDT in B-factor column

---

## 5. Experiment 1: Within-Tool Quality Assessment

**Objective:** Establish baseline accuracy for each prediction tool by comparing predictions against experimentally determined structures.

**Workflow:** [`cwl/workflows/experiment1-within-tool.cwl`](cwl/workflows/experiment1-within-tool.cwl)

### 5.1 Design

Each tool predicts structures for all 10 pilot targets using default settings (with MSA where applicable). Each prediction is compared against the corresponding experimental PDB structure using `protein_compare`.

### 5.2 Step-by-Step Procedure

1. **Prepare inputs**: Ensure all FASTA files, Boltz YAML manifests, and precomputed MSAs are available in `data/`
2. **Run predictions** (scatter over targets x tools):
   - AlphaFold2: Predict each target using precomputed JackHMMER MSA (its native method)
   - Boltz: Predict each target using YAML manifest with MMseqs2 MSA
   - Chai: Predict each target with MMseqs2 MSA
   - ESMFold: Predict each target (sequence only)
3. **Compare structures**: For each (target, tool) pair, run `protein_compare` between the predicted PDB and the experimental PDB
4. **Collect metrics**: Aggregate all JSON comparison outputs into a unified CSV

### 5.3 Expected Outputs

- `results/experiment1/{tool}/{target_id}/predicted.pdb` — Predicted structures
- `results/experiment1/{tool}/{target_id}/metrics.json` — Per-comparison metrics
- `results/all_metrics.csv` — Aggregated results (after running `collect_metrics.py`)

### 5.4 Key Questions Addressed

- Which tool achieves the highest average TM-score across all targets?
- Do all tools struggle with the same targets, or do different tools have different failure modes?
- How do pLDDT scores correlate with actual accuracy for each tool?
- Do "easy" targets (1UBQ, 4LZT) converge to similar accuracy across tools while "hard" targets (7MRX, 7S0B) diverge?

### 5.5 Submission

```bash
gowe submit cwl/workflows/experiment1-within-tool.cwl \
  --input target_fastas=data/*.fasta \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb
```

---

## 6. Experiment 2: Cross-Tool Comparison

**Objective:** Quantify structural agreement and divergence between predictions from different tools for the same protein targets.

**Workflow:** [`cwl/workflows/experiment2-across-tools.cwl`](cwl/workflows/experiment2-across-tools.cwl)

### 6.1 Design

For each target, all predicted structures (from Experiment 1) are compared pairwise using `batch-compare`. This reveals whether tools converge on similar structures or produce meaningfully different predictions.

### 6.2 Step-by-Step Procedure

1. **Collect predictions**: Gather all predicted PDB files from Experiment 1 for each target
2. **Batch pairwise comparison**: For each target, run `batch-compare` in all-vs-all mode across the 4 tool predictions
3. **Compute agreement matrices**: Generate TM-score, RMSD, and contact Jaccard matrices for each target
4. **Aggregate results**: Combine cross-tool metrics into the unified CSV

### 6.3 Comparison Matrix

For each target protein, we compute a 4x4 comparison matrix:

|  | AlphaFold2 | Boltz | Chai | ESMFold |
|--|-----------|-------|------|---------|
| **AlphaFold2** | - | vs | vs | vs |
| **Boltz** | vs | - | vs | vs |
| **Chai** | vs | vs | - | vs |
| **ESMFold** | vs | vs | vs | - |

This yields 6 unique pairwise comparisons per target, 60 total across all 10 targets.

### 6.4 Expected Outputs

- `results/experiment2/{target_id}/batch_metrics.json` — All pairwise comparisons for each target
- Cross-tool agreement heatmaps (generated by `plot_results.py`)

### 6.5 Key Questions Addressed

- Which pairs of tools produce the most similar predictions?
- Does ESMFold (single-sequence) produce systematically different structures from MSA-based tools?
- Are there targets where tools strongly disagree, suggesting multiple plausible folds?
- Do the MSA-based tools (AlphaFold2, Boltz, Chai) form a consensus that differs from ESMFold?

### 6.6 Submission

```bash
gowe submit cwl/workflows/experiment2-across-tools.cwl \
  --input predictions_dir=results/experiment1/
```

---

## 7. Experiment 3: MSA Impact Analysis

**Objective:** Quantify how MSA availability and source affect prediction quality by comparing each tool in both MSA and no-MSA modes.

**Workflow:** [`cwl/workflows/experiment3-msa-impact.cwl`](cwl/workflows/experiment3-msa-impact.cwl)

### 7.1 Design

Each MSA-capable tool is run under three conditions:
1. **no_msa**: Single-sequence prediction (no evolutionary information)
2. **msa_mmseqs2**: Prediction using MMseqs2-generated MSA
3. **msa_jackhmmer**: Prediction using JackHMMER-generated MSA

ESMFold runs only under `no_msa` since it cannot use MSA input.

### 7.2 Conditions Matrix

| Tool | no_msa | msa_mmseqs2 | msa_jackhmmer |
|------|--------|-------------|---------------|
| AlphaFold2 | Single-seq A3M | MMseqs2 A3M | JackHMMER A3M |
| Boltz | No MSA field | MMseqs2 A3M | JackHMMER A3M |
| Chai | No MSA file | MMseqs2 A3M | JackHMMER A3M |
| ESMFold | Sequence only | N/A | N/A |

Total prediction runs: (3 tools x 3 conditions + 1 tool x 1 condition) x 10 targets = **100 predictions**

### 7.3 Step-by-Step Procedure

1. **Prepare no-MSA inputs**:
   - AlphaFold2: Create single-sequence A3M files (query sequence only, in A3M format)
   - Boltz: Create YAML manifests without `msa:` field
   - Chai: Omit MSA file argument
2. **Prepare MSA inputs**:
   - Verify MMseqs2 A3M files exist in `data/msas/mmseqs2/`
   - Verify JackHMMER A3M files exist in `data/msas/jackhmmer/`
3. **Run predictions** (scatter over targets x tools x conditions):
   - For each combination, invoke the appropriate CWL tool with or without MSA
4. **Compare to experimental**: Each prediction is compared against the experimental PDB
5. **Compute MSA impact delta**: For each (target, tool), calculate the change in metrics between MSA and no-MSA conditions

### 7.4 Expected Outputs

- `results/experiment3/{tool}/{condition}/{target_id}/predicted.pdb`
- `results/experiment3/{tool}/{condition}/{target_id}/metrics.json`
- Delta analysis showing metric improvement from MSA inclusion

### 7.5 Key Questions Addressed

- How much does MSA improve TM-score on average? Per tool?
- Does the MSA source matter? Is MMseqs2 or JackHMMER better for each tool?
- Are some targets equally well-predicted with or without MSA (strong sequence signal)?
- For which fold classes does MSA matter most?
- How does pLDDT change with MSA availability? Do tools become more confident with MSA even when accuracy doesn't improve much?

### 7.6 Submission

```bash
gowe submit cwl/workflows/experiment3-msa-impact.cwl \
  --input target_fastas=data/*.fasta \
  --input msas_mmseqs2=data/msas/mmseqs2/*.a3m \
  --input msas_jackhmmer=data/msas/jackhmmer/*.a3m \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb
```

---

## 8. Experiment 4: MSA Depth Sensitivity

**Objective:** Determine the relationship between MSA depth and prediction quality, identifying optimal MSA sizes and how MSA source influences the depth-quality curve.

**Workflow:** [`cwl/workflows/experiment4-msa-depth.cwl`](cwl/workflows/experiment4-msa-depth.cwl)

### 8.1 Design

Full MSAs are subsampled to 10 controlled depths (1, 8, 16, 32, 64, 128, 256, 512, 1024, full). Each subsampled MSA is used as input to each MSA-capable tool, and predictions are compared against experimental structures.

### 8.2 Depth Levels

| Depth | Interpretation |
|-------|---------------|
| 1 | Single-sequence (no evolutionary information) |
| 8 | Minimal MSA (very few homologs) |
| 16 | Sparse MSA |
| 32 | Low-depth MSA |
| 64 | Moderate MSA |
| 128 | Standard depth (typical for many proteins) |
| 256 | Deep MSA |
| 512 | Very deep MSA |
| 1024 | Near-complete MSA |
| full | Complete MSA (all available sequences) |

### 8.3 Step-by-Step Procedure

1. **Generate subsampled MSAs**:
   - For each target and each MSA method (MMseqs2, JackHMMER):
     - Subsample the full MSA to each depth level
     - Use both random and diversity-weighted strategies
   - CWL tool: [`cwl/tools/subsample-msa.cwl`](cwl/tools/subsample-msa.cwl)
   - Python script: [`scripts/subsample_msa.py`](scripts/subsample_msa.py)
2. **Run predictions** (scatter over targets x tools x depths x MSA methods):
   - AlphaFold2, Boltz, Chai at each depth level
   - ESMFold at depth=1 only (baseline reference)
3. **Compare to experimental**: Each prediction compared against the experimental PDB
4. **Build depth-quality curves**: Plot metric (TM-score, RMSD, GDT-TS) as a function of MSA depth for each tool and MSA source

### 8.4 Scale

- 10 targets x 3 tools x 10 depths x 2 MSA sources = **600 predictions** (plus 10 ESMFold baselines)
- Each prediction generates one JSON metrics file
- All metrics aggregated into a single CSV for analysis

### 8.5 Expected Outputs

- `results/experiment4/{tool}/{msa_source}/depth_{N}/{target_id}/predicted.pdb`
- `results/experiment4/{tool}/{msa_source}/depth_{N}/{target_id}/metrics.json`
- Depth-quality curves (generated by `plot_results.py`)

### 8.6 Key Questions Addressed

- Is there a "saturation point" beyond which additional MSA sequences provide diminishing returns?
- Does AlphaFold2 require deeper MSAs than Boltz or Chai?
- Does diversity-weighted subsampling outperform random subsampling at low depths?
- At which depth does each tool achieve 90% of its full-MSA accuracy?
- Does the depth-quality relationship differ between MMseqs2 and JackHMMER MSAs?

### 8.7 Submission

```bash
gowe submit cwl/workflows/experiment4-msa-depth.cwl \
  --input target_fastas=data/*.fasta \
  --input msas_mmseqs2_full=data/msas/mmseqs2/*.a3m \
  --input msas_jackhmmer_full=data/msas/jackhmmer/*.a3m \
  --input target_experimental_pdbs=data/experimental/*_chain*.pdb \
  --input msa_depths="1,8,16,32,64,128,256,512,1024"
```

---

## 9. Metrics and Evaluation

### 9.1 Structure Comparison Tool

All structural comparisons use the `protein_compare` CLI from the [protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) toolkit.

**CWL tools:**
- [`cwl/tools/compare-structures.cwl`](cwl/tools/compare-structures.cwl) — Single pairwise comparison
- [`cwl/tools/batch-compare.cwl`](cwl/tools/batch-compare.cwl) — All-vs-all or all-vs-reference batch mode

### 9.2 Primary Metrics

| Metric | Range | Good Value | Use Case |
|--------|-------|------------|----------|
| TM-score | 0-1 | >0.5 (same fold), >0.7 (high similarity) | Global fold accuracy |
| RMSD (Å) | 0-inf | <2.0 Å (excellent) | Backbone deviation |
| GDT-TS | 0-100 | >70 (good), >90 (excellent) | CASP-style evaluation |
| GDT-HA | 0-100 | >50 (good) | High-accuracy discrimination |

### 9.3 Secondary Metrics

| Metric | Range | Use Case |
|--------|-------|----------|
| Weighted RMSD | 0-inf | pLDDT-weighted backbone deviation |
| Contact Jaccard | 0-1 | Contact map topology agreement |
| SS Agreement | 0-1 | Secondary structure prediction accuracy |
| Aligned length | 0-N | Number of structurally aligned residues |
| Sequence identity | 0-1 | Sequence identity in the structural alignment |

### 9.4 pLDDT-Based Metrics

These metrics evaluate the tools' intrinsic confidence and its relationship to actual accuracy.

| Metric | Range | Interpretation |
|--------|-------|---------------|
| Mean pLDDT (predicted) | 0-100 | Average confidence of the predicted structure |
| Mean pLDDT (reference) | 0-100 | Average B-factor/confidence of reference structure |
| High-confidence fraction | 0-1 | Proportion of residues with pLDDT >= 70 |
| Low-confidence fraction | 0-1 | Proportion of residues with pLDDT < 50 |
| High-confidence RMSD | 0-inf | RMSD over only confident residues |
| High-confidence TM-score | 0-1 | TM-score over only confident residues |
| pLDDT-accuracy correlation | -1 to 1 | Confidence calibration quality |

### 9.5 Metric Collection

**Script:** [`scripts/collect_metrics.py`](scripts/collect_metrics.py)

```bash
python scripts/collect_metrics.py --results-dir results/ --output results/all_metrics.csv
```

This script recursively scans the `results/` directory for JSON metrics files, infers experimental metadata (tool, MSA condition, MSA source, depth) from file paths, and writes a consolidated CSV with all columns listed in sections 9.2-9.4.

---

## 10. Execution and Orchestration

### 10.1 GoWe Workflow Engine

All experiments are executed through [GoWe](https://github.com/wilke/GoWe), a CWL v1.2-compatible workflow engine. GoWe manages:
- Dependency resolution between workflow steps
- Docker container lifecycle
- Input/output staging
- Scatter/gather parallelism
- Job tracking and status reporting

### 10.2 Docker Containers

| Container | Tool | Registry |
|-----------|------|----------|
| `wilke/alphafold` | AlphaFold2 | Docker Hub |
| `dxkb/boltz` | Boltz | Docker Hub |
| `dxkb/chai` | Chai | Docker Hub |
| `dxkb/esmfold` | ESMFold | Docker Hub |
| `dxkb/protein-compare` | protein_compare | Docker Hub |

### 10.3 Execution Order

```
Phase 1: Data Preparation
  ├── Download experimental PDBs (fetch-pdb.cwl)
  ├── Extract sequences (prepare_targets.py)
  └── Generate MSAs (generate_msas.py)
       ├── MMseqs2 → A3M
       └── JackHMMER → Stockholm → A3M

Phase 2: MSA Subsampling (Experiment 4 only)
  └── Subsample MSAs at each depth (subsample-msa.cwl)

Phase 3: Structure Prediction
  ├── Experiment 1: Default predictions (4 tools x 10 targets)
  ├── Experiment 3: MSA conditions (3 tools x 3 conditions x 10 targets)
  └── Experiment 4: Depth sweep (3 tools x 10 depths x 2 sources x 10 targets)

Phase 4: Structure Comparison
  ├── Experiment 1: Compare predictions vs experimental
  ├── Experiment 2: Cross-tool pairwise comparison
  ├── Experiment 3: Compare all conditions vs experimental
  └── Experiment 4: Compare all depth predictions vs experimental

Phase 5: Analysis
  ├── Collect all metrics into CSV (collect_metrics.py)
  └── Generate plots and figures (plot_results.py)
```

### 10.4 Monitoring

```bash
# Submit a workflow
gowe submit cwl/workflows/experiment1-within-tool.cwl --input ...

# Check job status
gowe status <submission_id>

# View logs
gowe logs <submission_id>
```

---

## 11. Analysis Pipeline

### 11.1 Metric Aggregation

**Script:** [`scripts/collect_metrics.py`](scripts/collect_metrics.py)

Scans all `results/experiment*/` directories for JSON metrics files and assembles them into `results/all_metrics.csv` with columns for target_id, tool, msa_condition, msa_source, msa_depth, and all structural and confidence metrics.

### 11.2 Visualization

**Script:** [`scripts/plot_results.py`](scripts/plot_results.py)

Generates the following analysis plots:

**Experiment 1 plots:**
- Per-tool TM-score bar chart across all targets
- Per-tool RMSD distribution (box plots)
- Target difficulty ranking (sorted by average TM-score)

**Experiment 2 plots:**
- Cross-tool TM-score agreement heatmaps (one per target)
- Consensus analysis: mean cross-tool agreement by target

**Experiment 3 plots:**
- MSA impact: paired bar charts showing metric change with/without MSA
- MSA source comparison: MMseqs2 vs JackHMMER accuracy per tool
- Per-target MSA sensitivity ranking

**Experiment 4 plots:**
- Depth-quality curves: TM-score vs MSA depth (one line per tool, faceted by MSA source)
- Saturation analysis: depth at which 90% of full-MSA accuracy is reached
- Subsampling strategy comparison: random vs diversity-weighted

**pLDDT analysis plots:**
- Intrinsic confidence: mean pLDDT by tool and MSA condition
- Confidence vs accuracy: scatter of pLDDT vs TM-score/RMSD
- MSA impact on confidence: how pLDDT changes with MSA availability
- High-confidence fraction: proportion of confident residues by tool
- Calibration curves: pLDDT-accuracy correlation by tool

### 11.3 Running the Analysis

```bash
# Aggregate all metrics
python scripts/collect_metrics.py --results-dir results/ --output results/all_metrics.csv

# Generate all plots
python scripts/plot_results.py --metrics results/all_metrics.csv --output-dir results/figures/
```

### 11.4 Dependencies

```bash
pip install pyyaml matplotlib seaborn pandas numpy
```

---

## Appendix: Repository Structure

```
ProteinFoldingApp/
├── EXPERIMENT_PLAN.md              ← This document
├── README.md                       ← Project overview and quickstart
├── CLAUDE.md                       ← Development guidance
├── configs/
│   └── targets_pilot.yaml          ← Target protein configuration
├── cwl/
│   ├── tools/                      ← CWL CommandLineTool definitions
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
│   └── workflows/                  ← CWL Workflow definitions
│       ├── experiment1-within-tool.cwl
│       ├── experiment2-across-tools.cwl
│       ├── experiment3-msa-impact.cwl
│       └── experiment4-msa-depth.cwl
├── scripts/
│   ├── prepare_targets.py
│   ├── generate_msas.py
│   ├── subsample_msa.py
│   ├── collect_metrics.py
│   └── plot_results.py
├── data/                           ← Generated data (partially gitignored)
│   ├── targets.csv
│   ├── experimental/
│   └── msas/
│       ├── mmseqs2/
│       ├── jackhmmer/
│       └── subsampled/
└── results/                        ← Workflow outputs (gitignored)
```

# MSA Generation Report

**Date:** 2026-02-25
**System:** 384 cores, 1.5 TiB RAM, no swap, local NVMe storage
**Runtime:** Apptainer containers (`staphb/hmmer:latest`, `staphb/mmseqs2:latest`)
**Orchestration:** GoWe CWL v1.2 engine (`cwl-runner --parallel`)

---

## 1. Experimental Design

### Objective

Precompute Multiple Sequence Alignments (MSAs) for 10 pilot protein targets using two MSA tools against two sequence databases, producing a 2x2 matrix of MSA results per target. These 40 MSA files serve as shared input for downstream experiments comparing prediction quality across tools, MSA methods, and MSA depths.

### Targets

| PDB ID | Chain | Protein | Category | Residues | Resolution | Fold Class |
|--------|-------|---------|----------|----------|------------|------------|
| 1L2Y | A | Trp-cage miniprotein | easy_small | 20 | NMR | mini-protein |
| 1UBQ | A | Ubiquitin | easy_small | 76 | 1.8 A | all-beta |
| 1TEN | A | Tenascin FN-III | beta | 89 | 1.8 A | all-beta |
| 4LZT | A | Lysozyme | enzyme | 129 | 0.94 A | alpha-beta |
| 1BL8 | A | Galectin-1 | beta | 135 | 1.7 A | all-beta |
| 7MRX | B | CASP14 T1091 | hard | 141 | 1.6 A | novel |
| 1MBN | A | Myoglobin | alpha | 153 | 1.4 A | all-alpha |
| 7S0B | A | CASP15 target | hard | 197 | 1.85 A | novel |
| 1AKE | A | Adenylate kinase | alpha_beta | 214 | 1.63 A | alpha-beta |
| 2SRC | A | Src tyrosine kinase | multi | 452 | 1.5 A | multi-domain |

### MSA Methods and Databases

| Tool | Database | File Size | Search Parameters |
|------|----------|-----------|-------------------|
| JackHMMER (HMMER 3.x) | UniRef90 FASTA | 84 GB | `-E 0.0001 --incE 0.0001 -N 3 --cpu 64` |
| JackHMMER (HMMER 3.x) | UniRef30 FASTA | 165 GB | `-E 0.0001 --incE 0.0001 -N 3 --cpu 64` |
| MMseqs2 | UniRef90 (indexed) | ~430 GB index | `-s 7.5 --max-seqs 10000 -e 0.001 --threads 64` |
| MMseqs2 | UniRef30/ColabFold (indexed) | ~434 GB index | `-s 7.5 --max-seqs 10000 -e 0.001 --threads 64` |

JackHMMER performs 3 iterative profile-HMM searches directly against FASTA files. MMseqs2 uses a prefilter/align/cluster pipeline against pre-indexed databases.

### Workflow Architecture

Two separate CWL workflows were used to accommodate different memory profiles:

```
generate-msas-jackhmmer.cwl  (-j 6, memory-light)
  scatter(target_fastas):
    jackhmmer_uniref90  ->  sto_to_a3m_uniref90
    jackhmmer_uniref30  ->  sto_to_a3m_uniref30

generate-msas-mmseqs2.cwl  (-j 2, memory-heavy)
  scatter(target_fastas):
    mmseqs2_uniref90
    mmseqs2_uniref30
```

The workflows were split after an initial combined run (`-j 6`) hit 98.8% memory (1493 GB / 1511 GB) due to concurrent MMseqs2 prefilter processes each allocating ~430 GB.

---

## 2. Runtime Metrics

### JackHMMER Workflow

- **Parallelism:** `-j 6` (6 concurrent jobs across all scatter iterations)
- **Wall time:** 1h 27m (21:34 - 23:01)
- **Peak memory:** 108 GB (7.1%)
- **Peak load:** 104

JackHMMER reads the database FASTA sequentially with memory-mapped I/O. Each process uses ~600 MB regardless of database or query size, making it safe to run at high parallelism.

**Per-database timing (from log timestamps):**

| Step | Jobs | First launch | Last completion | Notes |
|------|------|-------------|-----------------|-------|
| jackhmmer_uniref90 | 10 | 21:34 | ~22:42 | 68 min |
| jackhmmer_uniref30 | 10 | 21:34 | ~22:57 | 83 min |
| sto_to_a3m (uniref90) | 10 | 22:42 | ~22:43 | <1 min |
| sto_to_a3m (uniref30) | 10 | 22:57 | ~23:01 | <4 min |

**Scatter barrier observed:** The `sto_to_a3m` conversion steps could not begin until ALL 10 scatter iterations of their upstream `jackhmmer` step completed (CWL scatter semantics require the full output array). The first UniRef90 search (1L2Y) finished at 21:48 but waited 54 minutes for the last (7MRX) to finish at 22:42 before conversion started. This is a known CWL limitation solvable with subworkflow wrapping.

### MMseqs2 Workflow

- **Parallelism:** `-j 2` (2 concurrent jobs)
- **Wall time:** 2h 26m (22:56 - 01:22)
- **Peak memory:** 896 GB (59.3%)
- **Peak load:** 132

MMseqs2 prefilter loads the full database index into memory (~430 GB per job). With `-j 2`, peak memory reached ~896 GB when both slots ran prefilter concurrently.

**Per-database average job duration:**

| Database | Avg duration | Range | Dominant cost |
|----------|-------------|-------|---------------|
| UniRef30 (ColabFold) | 16m 24s | 9 - 19 min | Prefilter: DB load + k-mer scan |
| UniRef90 | 11m 40s | 8 - 25 min | Prefilter: DB load + k-mer scan |

**Setup vs compute (memory-based phase analysis):** Each MMseqs2 job cycles through prefilter (memory > 400 GB, ~50-60% of job time) and align/result2msa (memory < 100 GB, ~40-50%). The prefilter phase is the bottleneck: it loads and scans the full database index for each query independently.

### Combined Resource Usage

| Metric | JackHMMER | MMseqs2 |
|--------|-----------|---------|
| Wall time | 1h 27m | 2h 26m |
| Parallelism | 6 concurrent | 2 concurrent |
| Peak memory | 108 GB (7%) | 896 GB (59%) |
| Memory per job | ~600 MB | ~430 GB |
| Total CPU time | ~14,000 CPU-min | ~5,000 CPU-min |
| Output size | 35 GB | 34 MB |

---

## 3. MSA Results

### Sequence Counts per Target

| Target (residues) | JH/UniRef90 | JH/UniRef30 | MM/UniRef90 | MM/UniRef30 |
|--------------------|------------|------------|------------|------------|
| 1L2Y (20) | 31 | 38 | 1 | 1 |
| 1UBQ (76) | 78,841 | 106,749 | 10,001 | 10,565 |
| 1TEN (89) | 1,146,589 | 2,276,820 | 5,324 | 10,230 |
| 4LZT (129) | 6,095 | 8,305 | 4,454 | 6,253 |
| 1BL8 (135) | 146,152 | 275,873 | 10,001 | 10,565 |
| 7MRX (141) | 12,957 | 17,012 | 1,411 | 2,435 |
| 1MBN (153) | 63,384 | 126,768 | 1,527 | 3,920 |
| 7S0B (197) | 886,331 | 1,546,485 | 10,001 | 10,565 |
| 1AKE (214) | 67,400 | 146,979 | 10,001 | 10,565 |
| 2SRC (452) | 1,906,547 | 3,279,596 | 10,001 | 10,565 |

### File Sizes

| Target | JH/UniRef90 | JH/UniRef30 | MM/UniRef90 | MM/UniRef30 |
|--------|------------|------------|------------|------------|
| 1L2Y | 1.5 KB | 2.2 KB | 29 B | 29 B |
| 1UBQ | 51 MB | 67 MB | 1.3 MB | 1.4 MB |
| 1TEN | 907 MB | 1.9 GB | 801 KB | 1.6 MB |
| 4LZT | 3.2 MB | 3.9 MB | 843 KB | 1.2 MB |
| 1BL8 | 100 MB | 183 MB | 1.6 MB | 1.7 MB |
| 7MRX | 3.9 MB | 5.0 MB | 207 KB | 358 KB |
| 1MBN | 30 MB | 56 MB | 324 KB | 833 KB |
| 7S0B | 1.7 GB | 2.8 GB | 2.8 MB | 2.9 MB |
| 1AKE | 114 MB | 253 MB | 2.7 MB | 2.9 MB |
| 2SRC | 9.8 GB | 18 GB | 5.0 MB | 5.3 MB |
| **Total** | **~12.7 GB** | **~23 GB** | **~16 MB** | **~18 MB** |

---

## 4. Analysis

### MSA Depth: JackHMMER vs MMseqs2

The most striking result is the **1000x difference in MSA sizes** between JackHMMER and MMseqs2. JackHMMER returns all significant hits (up to millions of sequences), while MMseqs2 caps output at `--max-seqs 10,000`. For well-conserved proteins like 2SRC, JackHMMER finds 1.9M-3.3M homologs compared to MMseqs2's hard cap of 10,001-10,565.

This difference will directly impact Experiment 4 (MSA depth sensitivity): JackHMMER MSAs provide the full range of subsampling depths (1 to 3M+), while MMseqs2 MSAs are limited to a maximum of ~10,000 sequences.

### UniRef30 vs UniRef90

JackHMMER consistently finds **1.5-2x more sequences** in UniRef30 than UniRef90 for the same target, despite UniRef30 being a more clustered (less redundant) database. This is because:

1. UniRef30 clusters are represented by consensus sequences that capture broader sequence diversity
2. The UniRef30 FASTA is 2x larger (165 GB vs 84 GB), containing more representative sequences
3. JackHMMER's iterative profile-HMM approach amplifies these differences across 3 iterations

MMseqs2 shows the same UniRef30 > UniRef90 trend but the effect is smaller, likely dampened by the `--max-seqs` cap.

### Hard Targets (7MRX, 7S0B)

The CASP targets show divergent behavior:
- **7MRX** (CASP14 novel fold): Very few homologs across all methods (1,411-17,012). MMseqs2 found only 1,411 in UniRef90 and 2,435 in UniRef30 - these shallow MSAs may challenge prediction quality.
- **7S0B** (CASP15): Unexpectedly rich MSAs (886K-1.5M via JackHMMER, 10K via MMseqs2), suggesting this protein has extensive homology despite being a recent CASP target.

### 1L2Y (Trp-cage): Edge Case

The 20-residue Trp-cage miniprotein yielded essentially no MSA: 31 sequences via JackHMMER and only 1 (itself) via MMseqs2. This is expected for a synthetic miniprotein with no natural homologs. Structure prediction for 1L2Y will rely entirely on single-sequence methods.

### Memory Bottleneck Analysis

MMseqs2's prefilter phase is the primary resource bottleneck. Each prefilter invocation loads the full database index into memory (~430 GB), and this memory is **not shared** across concurrent processes despite using mmap. The prefilter accounts for ~50-60% of each job's runtime, with the actual alignment phase using negligible memory.

This per-process memory allocation forced the split to `-j 2`, limiting MMseqs2 throughput to 2 concurrent jobs. By contrast, JackHMMER's sequential FASTA reading uses only ~600 MB per process, allowing `-j 6` (12x less memory per slot).

---

## 5. MSA Depth Disparity: Parameter Analysis and Comparability

### The Problem

The most significant methodological concern in these results is the **1000x difference in MSA depth** between JackHMMER and MMseqs2. For 2SRC, JackHMMER returns 1.9M sequences while MMseqs2 returns exactly 10,001. This is not a sensitivity difference between the tools — it is an artifact of the `--max-seqs` parameter.

### Command-Line Parameters as Used

**JackHMMER:**
```
jackhmmer -A output.sto -o output.log \
  --cpu 64 -E 0.0001 --incE 0.0001 -N 3 \
  query.fasta database.fasta
```

| Parameter | Value | Effect |
|-----------|-------|--------|
| `-N 3` | 3 iterations | Iterative profile-HMM refinement; builds a profile from hits, re-searches |
| `-E 0.0001` | Sequence E-value | Only report sequences with E-value < 1e-4 |
| `--incE 0.0001` | Inclusion E-value | Only include sequences with E-value < 1e-4 in the profile for next iteration |
| `--cpu 64` | 64 threads | Parallelism |
| *(no max-seqs)* | **unlimited** | **Returns ALL sequences passing the E-value threshold** |

**MMseqs2:**
```
mmseqs search queryDB targetDB resultDB tmp \
  -s 7.5 --max-seqs 10000 -e 0.001 --threads 64

mmseqs result2msa queryDB targetDB resultDB msaDB \
  --msa-format-mode 6 --threads 64
```

| Parameter | Value | Effect |
|-----------|-------|--------|
| `-s 7.5` | Sensitivity | High sensitivity (scale 1-8); controls k-mer prefilter stringency |
| `-e 0.001` | E-value | Report hits with E-value < 1e-3 |
| `--max-seqs 10000` | **Hard cap** | **Retain at most 10,000 hits per query, discard the rest** |
| `--msa-format-mode 6` | A3M output | Produce A3M-format MSA from search results |
| `--threads 64` | 64 threads | Parallelism |

### Root Cause of Depth Disparity

The `--max-seqs 10000` parameter in MMseqs2 is the primary driver. For well-conserved proteins (2SRC, 7S0B, 1TEN), JackHMMER finds hundreds of thousands to millions of homologs, but MMseqs2 truncates at exactly 10,000 (10,001 including the query, or 10,565 for UniRef30 due to tied scores at the boundary). The evidence:

| Target | JH/UniRef90 | MM/UniRef90 | MM hit cap? |
|--------|------------|------------|-------------|
| 2SRC | 1,906,547 | 10,001 | **Yes** (capped) |
| 7S0B | 886,331 | 10,001 | **Yes** (capped) |
| 1TEN | 1,146,589 | 5,324 | No |
| 1AKE | 67,400 | 10,001 | **Yes** (capped) |
| 1BL8 | 146,152 | 10,001 | **Yes** (capped) |
| 1UBQ | 78,841 | 10,001 | **Yes** (capped) |
| 1MBN | 63,384 | 1,527 | No |
| 7MRX | 12,957 | 1,411 | No |
| 4LZT | 6,095 | 4,454 | No |
| 1L2Y | 31 | 1 | No |

Six of 10 targets hit the MMseqs2 cap. For these, the reported MSA depth is meaningless as a measure of homology — it simply reflects the parameter setting.

A secondary factor is the **E-value threshold**: JackHMMER uses `-E 0.0001` (1e-4) while MMseqs2 uses `-e 0.001` (1e-3). Counterintuitively, MMseqs2's more permissive E-value should yield *more* hits, but the `--max-seqs` cap dominates. For the uncapped targets (1MBN, 7MRX, 4LZT, 1TEN), the gap between tools ranges from 1.4x to 215x — reflecting genuine algorithmic differences in sensitivity between iterative profile-HMM search (JackHMMER) and k-mer prefilter + ungapped alignment (MMseqs2).

### Additional Algorithmic Differences

Beyond the parameter settings, the tools differ fundamentally:

1. **Search strategy:** JackHMMER performs iterative profile-HMM searches (3 rounds), building progressively more sensitive profiles. MMseqs2 uses a fast k-mer prefilter followed by ungapped/gapped alignment — no iteration. The iterative approach finds more remote homologs, especially after 2-3 rounds of profile refinement.

2. **Database format:** JackHMMER searches raw FASTA files sequentially. MMseqs2 requires a pre-indexed database with k-mer lookup tables, which enables speed but limits sensitivity to the k-mer seeding step.

3. **Scoring model:** JackHMMER uses a full probabilistic profile-HMM with position-specific scoring. MMseqs2 uses substitution matrices (BLOSUM62) with composition bias correction.

4. **Redundancy in hits:** JackHMMER does not deduplicate hits — if a sequence appears in multiple rounds, it appears once in the final MSA. MMseqs2's prefilter naturally deduplicates via its internal clustering.

### Making the Results Comparable

To enable fair comparison between JackHMMER and MMseqs2 MSAs in downstream experiments, several approaches can be used independently or in combination:

#### Option A: Equalize by Subsampling (Recommended for Experiment 4)

Subsample both tools' MSAs to the same depth levels. This is already planned for Experiment 4:

```
Depths: 1, 8, 16, 32, 64, 128, 256, 512, 1024, full
```

At depths up to 1,024, both tools provide enough sequences (except 1L2Y). The "full" depth will differ between tools, which is itself an informative comparison.

#### Option B: Remove the MMseqs2 Cap

Re-run MMseqs2 with `--max-seqs 300000` (or larger) to let it return all hits within the E-value threshold:

```bash
mmseqs search queryDB targetDB resultDB tmp \
  -s 7.5 --max-seqs 300000 -e 0.001 --threads 64
```

This would reveal MMseqs2's true sensitivity (before the cap). The value 300,000 is used by ColabFold for structure prediction. Note: this may increase memory requirements for the result database.

#### Option C: Equalize E-value Thresholds

Run both tools with the same E-value threshold to isolate the algorithmic differences:

```
JackHMMER:  -E 0.001 --incE 0.001    (relax from 1e-4 to 1e-3)
   -- or --
MMseqs2:    -e 0.0001                 (tighten from 1e-3 to 1e-4)
```

#### Option D: Cap JackHMMER Output to Match

Post-process JackHMMER MSAs to retain only the top 10,000 sequences by bitscore, matching MMseqs2's cap. This controls for depth while preserving each tool's ranking of homologs:

```python
# Subsample JackHMMER to top-N by bitscore (from Stockholm file)
# Then both tools are compared on their top 10,000 hits only
```

### Recommendation

For the current experimental design, **Option A (subsampling) combined with Option B (uncapped re-run)** provides the most informative comparison:

- Experiment 3 (MSA impact): Use each tool's full output as-is. The depth difference is itself a characteristic of the tool configuration.
- Experiment 4 (MSA depth): Subsample both to matched depths. At equal depth, differences reflect MSA *quality* (which homologs were selected), not quantity.
- Future re-run: Remove the `--max-seqs` cap from MMseqs2 to measure its true sensitivity for the uncapped comparison.

---

## 6. Optimization Opportunities

Several approaches could significantly reduce MSA generation time for future runs:

### Batch Query Mode (Highest Impact)

Both tools support multi-FASTA input, processing all queries against the database in a single invocation:

- **MMseqs2:** `mmseqs easy-search multi_query.fasta targetDB result.m8 tmp` loads the database once for all queries, eliminating ~80 minutes of redundant DB loading across 20 jobs.
- **JackHMMER:** Accepts multi-FASTA and processes queries sequentially while keeping the database memory-mapped, benefiting from OS page cache persistence.

Estimated speedup: MMseqs2 wall time from 2h 26m to ~30 min; JackHMMER from 1h 27m to ~1h 10m.

### Database Pre-indexing and Memory Pinning

```bash
mmseqs createindex targetDB tmp --threads 32    # one-time
mmseqs search queryDB targetDB resultDB tmp --db-load-mode 3  # preload into RAM
```

Pre-computing the k-mer index and using `--db-load-mode 3` (mmap + touch) reduces per-search initialization from ~30s to ~0.05s.

### PyHMMER (JackHMMER Alternative)

Python bindings to HMMER3 that load the database once in-process with improved multi-threading (~96% parallel efficiency vs ~35% for CLI HMMER). Published benchmarks show a **72% runtime reduction** ([Larralde & Zeller, Bioinformatics 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10159651/)).

### MMseqs2 Local Server

A persistent local service that keeps the database indexed in memory, accepting queries via REST API. Eliminates all DB loading overhead for repeated searches ([Mirdita et al., Bioinformatics 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6691333/)). Most beneficial for interactive or streaming workloads; for batch mode the multi-FASTA approach is simpler.

### GPU-Accelerated MMseqs2

Recent versions support `--gpu 1` for GPU-accelerated prefiltering ([Steinegger et al., Nature Methods 2025](https://www.nature.com/articles/s41592-025-02819-8)), which could dramatically reduce the prefilter bottleneck.

---

## 7. Output File Organization

All 40 MSA files are stored in:

```
data/msas/
  jackhmmer/    (20 files, 35 GB)
    {pdbid}_chain{X}.jackhmmer.uniref90.a3m
    {pdbid}_chain{X}.jackhmmer.uniref30.a3m
  mmseqs2/      (20 files, 34 MB)
    {pdbid}_chain{X}.mmseqs2.uniref90.a3m
    {pdbid}_chain{X}.mmseqs2.uniref30.a3m
```

These MSAs are ready for:
- **Experiment 1** (within-tool accuracy): Predictions with tool-native MSA input
- **Experiment 3** (MSA impact): Predictions with vs without MSA
- **Experiment 4** (MSA depth): Subsampled at depths 1, 8, 16, 32, 64, 128, 256, 512, 1024, full

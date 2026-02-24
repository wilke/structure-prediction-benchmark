cwlVersion: v1.2
class: Workflow
label: "Precompute MSAs for all pilot targets"
doc: |
  Generates multiple sequence alignments for all 10 pilot targets using
  both JackHMMER and MMseqs2 against both UniRef90 and UniRef30 databases.

  The precomputed MSAs are reused by Experiments 1, 3, and 4 to compare
  the impact of different MSA tools and databases on prediction quality.

  Four combinations per target (scattered):
    target_fasta → jackhmmer (UniRef90) → sto-to-a3m → A3M
    target_fasta → jackhmmer (UniRef30) → sto-to-a3m → A3M
    target_fasta → mmseqs2   (UniRef90)             → A3M
    target_fasta → mmseqs2   (UniRef30)             → A3M

  Output naming: ${ID}.${TOOL}.${DB}.${SUFFIX}
    e.g., 1ubq_chainA.jackhmmer.uniref90.a3m
          1ubq_chainA.mmseqs2.uniref30.a3m

requirements:
  ScatterFeatureRequirement: {}
  StepInputExpressionRequirement: {}
  InlineJavascriptRequirement: {}

inputs:
  target_fastas:
    type: File[]
    doc: "Array of target FASTA files (10 pilot targets)"

  uniref90_fasta:
    type: File
    doc: "UniRef90 FASTA database for JackHMMER"

  uniref30_fasta:
    type: File
    doc: "UniRef30 FASTA database for JackHMMER"

  uniref90_mmseqs_db:
    type: Directory
    doc: "UniRef90 MMseqs2 database directory"

  uniref90_mmseqs_db_prefix:
    type: string
    default: "uniref90_db"
    doc: "Database prefix within the UniRef90 MMseqs2 directory"

  uniref30_mmseqs_db:
    type: Directory
    doc: "UniRef30 MMseqs2 database directory"

  uniref30_mmseqs_db_prefix:
    type: string
    default: "uniref30_2302"
    doc: "Database prefix within the UniRef30 MMseqs2 directory"

  jackhmmer_cpus:
    type: int
    default: 64
    doc: "CPU threads for JackHMMER"

  mmseqs2_threads:
    type: int
    default: 64
    doc: "CPU threads for MMseqs2"

steps:
  # === JackHMMER × UniRef90 ===
  jackhmmer_uniref90:
    run: ../tools/jackhmmer-msa.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      database: uniref90_fasta
      cpus: jackhmmer_cpus
      output_prefix:
        valueFrom: $(inputs.fasta.nameroot).jackhmmer.uniref90
    out: [msa_sto, search_log]

  sto_to_a3m_jackhmmer_uniref90:
    run: ../tools/sto-to-a3m.cwl
    scatter: sto_file
    in:
      sto_file: jackhmmer_uniref90/msa_sto
      output_prefix:
        valueFrom: $(inputs.sto_file.nameroot.replace('.jackhmmer.uniref90', '')).jackhmmer.uniref90
    out: [a3m_file]

  # === JackHMMER × UniRef30 ===
  jackhmmer_uniref30:
    run: ../tools/jackhmmer-msa.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      database: uniref30_fasta
      cpus: jackhmmer_cpus
      output_prefix:
        valueFrom: $(inputs.fasta.nameroot).jackhmmer.uniref30
    out: [msa_sto, search_log]

  sto_to_a3m_jackhmmer_uniref30:
    run: ../tools/sto-to-a3m.cwl
    scatter: sto_file
    in:
      sto_file: jackhmmer_uniref30/msa_sto
      output_prefix:
        valueFrom: $(inputs.sto_file.nameroot.replace('.jackhmmer.uniref30', '')).jackhmmer.uniref30
    out: [a3m_file]

  # === MMseqs2 × UniRef90 ===
  mmseqs2_uniref90:
    run: ../tools/mmseqs2-msa.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      database: uniref90_mmseqs_db
      db_prefix: uniref90_mmseqs_db_prefix
      threads: mmseqs2_threads
      output_prefix:
        valueFrom: $(inputs.fasta.nameroot).mmseqs2.uniref90
    out: [msa_a3m]

  # === MMseqs2 × UniRef30 ===
  mmseqs2_uniref30:
    run: ../tools/mmseqs2-msa.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      database: uniref30_mmseqs_db
      db_prefix: uniref30_mmseqs_db_prefix
      threads: mmseqs2_threads
      output_prefix:
        valueFrom: $(inputs.fasta.nameroot).mmseqs2.uniref30
    out: [msa_a3m]

outputs:
  jackhmmer_uniref90_msas:
    type: File[]
    outputSource: sto_to_a3m_jackhmmer_uniref90/a3m_file
    doc: "A3M MSAs from JackHMMER/UniRef90 (one per target)"

  jackhmmer_uniref30_msas:
    type: File[]
    outputSource: sto_to_a3m_jackhmmer_uniref30/a3m_file
    doc: "A3M MSAs from JackHMMER/UniRef30 (one per target)"

  mmseqs2_uniref90_msas:
    type: File[]
    outputSource: mmseqs2_uniref90/msa_a3m
    doc: "A3M MSAs from MMseqs2/UniRef90 (one per target)"

  mmseqs2_uniref30_msas:
    type: File[]
    outputSource: mmseqs2_uniref30/msa_a3m
    doc: "A3M MSAs from MMseqs2/UniRef30 (one per target)"

  jackhmmer_uniref90_logs:
    type: File[]
    outputSource: jackhmmer_uniref90/search_log
    doc: "JackHMMER/UniRef90 search logs (one per target)"

  jackhmmer_uniref30_logs:
    type: File[]
    outputSource: jackhmmer_uniref30/search_log
    doc: "JackHMMER/UniRef30 search logs (one per target)"

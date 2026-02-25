cwlVersion: v1.2
class: Workflow
label: "Precompute MSAs via MMseqs2 (UniRef90 + UniRef30)"
doc: |
  MMseqs2-only MSA generation for all pilot targets against both
  UniRef90 and UniRef30 databases. Memory-heavy (~430 GB per job
  due to database memory-mapping), so must run at low parallelism (-j 2).

  Output naming: ${ID}.mmseqs2.${DB}.a3m
    e.g., 1ubq_chainA.mmseqs2.uniref90.a3m

requirements:
  ScatterFeatureRequirement: {}
  StepInputExpressionRequirement: {}
  InlineJavascriptRequirement: {}

inputs:
  target_fastas:
    type: File[]
    doc: "Array of target FASTA files (10 pilot targets)"

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

  mmseqs2_threads:
    type: int
    default: 64
    doc: "CPU threads for MMseqs2"

steps:
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
  mmseqs2_uniref90_msas:
    type: File[]
    outputSource: mmseqs2_uniref90/msa_a3m
    doc: "A3M MSAs from MMseqs2/UniRef90 (one per target)"

  mmseqs2_uniref30_msas:
    type: File[]
    outputSource: mmseqs2_uniref30/msa_a3m
    doc: "A3M MSAs from MMseqs2/UniRef30 (one per target)"

cwlVersion: v1.2
class: Workflow
label: "Precompute MSAs via JackHMMER (UniRef90 + UniRef30)"
doc: |
  JackHMMER-only MSA generation for all pilot targets against both
  UniRef90 and UniRef30 databases. Memory-light (~600 MB per job),
  so safe to run at high parallelism (-j 6).

  Output naming: ${ID}.jackhmmer.${DB}.a3m
    e.g., 1ubq_chainA.jackhmmer.uniref90.a3m

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

  jackhmmer_cpus:
    type: int
    default: 64
    doc: "CPU threads for JackHMMER"

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

outputs:
  jackhmmer_uniref90_msas:
    type: File[]
    outputSource: sto_to_a3m_jackhmmer_uniref90/a3m_file
    doc: "A3M MSAs from JackHMMER/UniRef90 (one per target)"

  jackhmmer_uniref30_msas:
    type: File[]
    outputSource: sto_to_a3m_jackhmmer_uniref30/a3m_file
    doc: "A3M MSAs from JackHMMER/UniRef30 (one per target)"

  jackhmmer_uniref90_logs:
    type: File[]
    outputSource: jackhmmer_uniref90/search_log
    doc: "JackHMMER/UniRef90 search logs (one per target)"

  jackhmmer_uniref30_logs:
    type: File[]
    outputSource: jackhmmer_uniref30/search_log
    doc: "JackHMMER/UniRef30 search logs (one per target)"

cwlVersion: v1.2
class: Workflow
label: "Experiment 3: MSA Impact on Prediction Quality"
doc: |
  Compares prediction quality with and without MSA for each tool that
  supports both modes (Boltz, Chai). AlphaFold2 uses single-sequence
  A3M as its "no-MSA" condition. ESMFold serves as the always-no-MSA baseline.

  Also compares MSA source impact: MMseqs2 vs JackHMMER.

  Conditions per tool:
    - no_msa: Single-sequence input (query only A3M)
    - msa_mmseqs2: Full MSA from MMseqs2
    - msa_jackhmmer: Full MSA from JackHMMER

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
  InlineJavascriptRequirement: {}
  MultipleInputFeatureRequirement: {}

inputs:
  target_fastas:
    type: File[]
    doc: "Target FASTA files"

  experimental_pdbs:
    type: File[]
    doc: "Experimental reference structures"

  # Boltz YAML variants (with and without MSA)
  boltz_yamls_no_msa:
    type: File[]
    doc: "Boltz YAMLs without MSA path"

  boltz_yamls_mmseqs2:
    type: File[]
    doc: "Boltz YAMLs with MMseqs2 MSA paths"

  boltz_yamls_jackhmmer:
    type: File[]
    doc: "Boltz YAMLs with JackHMMER MSA paths"

  # Precomputed MSA files for Chai
  msas_mmseqs2:
    type: File[]
    doc: "Precomputed MSAs from MMseqs2 (A3M)"

  msas_jackhmmer:
    type: File[]
    doc: "Precomputed MSAs from JackHMMER (A3M)"

  alphafold_data_dir:
    type: Directory
    doc: "AlphaFold databases"

  # Single-sequence MSA files for AF2 no-MSA condition
  single_seq_msas:
    type: File[]
    doc: "Single-sequence A3M files (query only, for AF2 no-MSA)"

steps:
  # ===== BOLTZ: No MSA =====
  boltz_no_msa:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: boltz_yamls_no_msa
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  boltz_no_msa_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: boltz_no_msa/predicted_cif
    out: [metrics_json]

  # ===== BOLTZ: MSA from MMseqs2 =====
  boltz_mmseqs2:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: boltz_yamls_mmseqs2
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  boltz_mmseqs2_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: boltz_mmseqs2/predicted_cif
    out: [metrics_json]

  # ===== BOLTZ: MSA from JackHMMER =====
  boltz_jackhmmer:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: boltz_yamls_jackhmmer
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  boltz_jackhmmer_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: boltz_jackhmmer/predicted_cif
    out: [metrics_json]

  # ===== CHAI: No MSA =====
  chai_no_msa:
    run: ../tools/chai-predict.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      num_models:
        default: 1
    out: [predicted_cif]

  chai_no_msa_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: chai_no_msa/predicted_cif
    out: [metrics_json]

  # ===== CHAI: MSA from MMseqs2 =====
  chai_mmseqs2:
    run: ../tools/chai-predict.cwl
    scatter: [fasta, msa_file]
    scatterMethod: dotproduct
    in:
      fasta: target_fastas
      msa_file: msas_mmseqs2
      num_models:
        default: 1
    out: [predicted_cif]

  chai_mmseqs2_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: chai_mmseqs2/predicted_cif
    out: [metrics_json]

  # ===== CHAI: MSA from JackHMMER =====
  chai_jackhmmer:
    run: ../tools/chai-predict.cwl
    scatter: [fasta, msa_file]
    scatterMethod: dotproduct
    in:
      fasta: target_fastas
      msa_file: msas_jackhmmer
      num_models:
        default: 1
    out: [predicted_cif]

  chai_jackhmmer_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: chai_jackhmmer/predicted_cif
    out: [metrics_json]

  # ===== ESMFold: always no-MSA (baseline) =====
  esmfold:
    run: ../tools/esmfold-predict.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      num_recycles:
        default: 4
    out: [predicted_pdb]

  esmfold_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: esmfold/predicted_pdb
    out: [metrics_json]

outputs:
  # Boltz results
  boltz_no_msa_metrics:
    type: File[]
    outputSource: boltz_no_msa_compare/metrics_json
  boltz_mmseqs2_metrics:
    type: File[]
    outputSource: boltz_mmseqs2_compare/metrics_json
  boltz_jackhmmer_metrics:
    type: File[]
    outputSource: boltz_jackhmmer_compare/metrics_json

  # Chai results
  chai_no_msa_metrics:
    type: File[]
    outputSource: chai_no_msa_compare/metrics_json
  chai_mmseqs2_metrics:
    type: File[]
    outputSource: chai_mmseqs2_compare/metrics_json
  chai_jackhmmer_metrics:
    type: File[]
    outputSource: chai_jackhmmer_compare/metrics_json

  # ESMFold baseline
  esmfold_metrics:
    type: File[]
    outputSource: esmfold_compare/metrics_json

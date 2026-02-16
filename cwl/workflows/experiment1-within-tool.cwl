cwlVersion: v1.2
class: Workflow
label: "Experiment 1: Experimental vs Predicted (Within Tool)"
doc: |
  For each target protein and each prediction tool, computes the predicted
  structure and compares it against the experimental (ground truth) structure.

  Produces per-tool quality metrics: TM-score, RMSD, GDT-TS, GDT-HA,
  weighted RMSD, contact Jaccard, and secondary structure agreement.

  Tools: AlphaFold2 (with MSA), Boltz (with MSA), Chai (with MSA), ESMFold (no MSA)

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
  InlineJavascriptRequirement: {}
  MultipleInputFeatureRequirement: {}

inputs:
  target_fastas:
    type: File[]
    doc: "Array of target FASTA files"

  target_experimental_pdbs:
    type: File[]
    doc: "Array of experimental PDB structures (same order as fastas)"

  boltz_yamls:
    type: File[]
    doc: "Array of Boltz YAML input files with MSA paths"

  alphafold_data_dir:
    type: Directory
    doc: "AlphaFold genetic databases directory"

steps:
  # --- AlphaFold2 predictions ---
  alphafold_predict:
    run: ../tools/alphafold-predict.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      data_dir: alphafold_data_dir
      model_preset:
        default: "monomer"
      db_preset:
        default: "full_dbs"
      use_precomputed_msas:
        default: false
    out: [predicted_pdb, ranking_json, timings_json]

  alphafold_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: target_experimental_pdbs
      predicted: alphafold_predict/predicted_pdb
    out: [metrics_json]

  # --- Boltz predictions ---
  boltz_predict:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: boltz_yamls
      use_msa_server:
        default: true
      recycling_steps:
        default: 3
      diffusion_samples:
        default: 1
    out: [predicted_cif, confidence_json]

  boltz_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: target_experimental_pdbs
      predicted: boltz_predict/predicted_cif
    out: [metrics_json]

  # --- Chai predictions ---
  chai_predict:
    run: ../tools/chai-predict.cwl
    scatter: fasta
    in:
      fasta: target_fastas
      use_msa_server:
        default: true
      num_models:
        default: 1
    out: [predicted_cif, scores_json]

  chai_compare:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: target_experimental_pdbs
      predicted: chai_predict/predicted_cif
    out: [metrics_json]

  # --- ESMFold predictions (baseline, no MSA) ---
  esmfold_predict:
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
      reference: target_experimental_pdbs
      predicted: esmfold_predict/predicted_pdb
    out: [metrics_json]

outputs:
  alphafold_metrics:
    type: File[]
    outputSource: alphafold_compare/metrics_json
    doc: "AlphaFold2 vs experimental comparison metrics"

  boltz_metrics:
    type: File[]
    outputSource: boltz_compare/metrics_json
    doc: "Boltz vs experimental comparison metrics"

  chai_metrics:
    type: File[]
    outputSource: chai_compare/metrics_json
    doc: "Chai vs experimental comparison metrics"

  esmfold_metrics:
    type: File[]
    outputSource: esmfold_compare/metrics_json
    doc: "ESMFold vs experimental comparison metrics"

  alphafold_structures:
    type: File[]
    outputSource: alphafold_predict/predicted_pdb
    doc: "AlphaFold2 predicted structures"

  boltz_structures:
    type: File[]
    outputSource: boltz_predict/predicted_cif
    doc: "Boltz predicted structures"

  chai_structures:
    type: File[]
    outputSource: chai_predict/predicted_cif
    doc: "Chai predicted structures"

  esmfold_structures:
    type: File[]
    outputSource: esmfold_predict/predicted_pdb
    doc: "ESMFold predicted structures"

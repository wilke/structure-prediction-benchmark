cwlVersion: v1.2
class: Workflow
label: "Experiment 4: MSA Depth Sensitivity Analysis"
doc: |
  Determines how MSA depth affects Boltz prediction quality by subsampling
  MSAs to various sizes and measuring prediction quality at each depth level.

  Tests all 4 MSA tool×database combinations:
    - MMseqs2 × UniRef30
    - MMseqs2 × UniRef90
    - JackHMMER × UniRef30
    - JackHMMER × UniRef90

  For each source × target × depth:
    1. Subsample MSA to target depth
    2. Generate Boltz input YAML from subsampled MSA
    3. Run Boltz prediction
    4. Compare to experimental structure

  Also runs full-depth predictions (no subsampling) for each source.

  MSA depths: 1 (single-seq), 8, 16, 32, 64, 128, 256, 512, 1024, full
  Scale: 4 sources × 10 targets × 10 depths = 400 predictions + 400 comparisons

requirements:
  ScatterFeatureRequirement: {}
  InlineJavascriptRequirement: {}

inputs:
  target_fastas:
    type: File[]
    doc: "Target FASTA files (for reference only; MSAs are precomputed)"

  experimental_pdbs:
    type: File[]
    doc: "Experimental reference structures (must match target order)"

  full_msas_mmseqs2_uniref30:
    type: File[]
    doc: "Full MSAs from MMseqs2 against UniRef30 (A3M format)"

  full_msas_mmseqs2_uniref90:
    type: File[]
    doc: "Full MSAs from MMseqs2 against UniRef90 (A3M format)"

  full_msas_jackhmmer_uniref30:
    type: File[]
    doc: "Full MSAs from JackHMMER against UniRef30 (A3M format)"

  full_msas_jackhmmer_uniref90:
    type: File[]
    doc: "Full MSAs from JackHMMER against UniRef90 (A3M format)"

  msa_depths:
    type: int[]
    default: [1, 8, 16, 32, 64, 128, 256, 512, 1024]
    doc: "MSA depth levels to test (excluding 'full')"

steps:
  # =========================================================================
  # Cross-product expansion: replicate PDBs to match flat_crossproduct output
  # (10 targets × N depths → 10*N entries, PDBs repeated N times each)
  # =========================================================================
  expand_pdbs:
    run:
      class: ExpressionTool
      requirements:
        InlineJavascriptRequirement: {}
      inputs:
        pdbs: File[]
        depths: int[]
      expression: |-
        ${
          var expanded = [];
          for (var i = 0; i < inputs.pdbs.length; i++) {
            for (var j = 0; j < inputs.depths.length; j++) {
              expanded.push(inputs.pdbs[i]);
            }
          }
          return {expanded_pdbs: expanded};
        }
      outputs:
        expanded_pdbs:
          type: File[]
    in:
      pdbs: experimental_pdbs
      depths: msa_depths
    out: [expanded_pdbs]

  # =========================================================================
  # MMseqs2 × UniRef30 — Depth sweep
  # =========================================================================
  subsample_mmseqs2_uniref30:
    run: ../tools/subsample-msa.cwl
    scatter: [msa_a3m, target_depth]
    scatterMethod: flat_crossproduct
    in:
      msa_a3m: full_msas_mmseqs2_uniref30
      target_depth: msa_depths
      random_seed:
        default: 42
    out: [subsampled_a3m]

  make_yaml_mmseqs2_uniref30:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: subsample_mmseqs2_uniref30/subsampled_a3m
    out: [boltz_yaml]

  predict_mmseqs2_uniref30:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_mmseqs2_uniref30/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_mmseqs2_uniref30:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: expand_pdbs/expanded_pdbs
      predicted: predict_mmseqs2_uniref30/predicted_cif
    out: [metrics_json]

  # MMseqs2 × UniRef30 — Full depth
  make_yaml_full_mmseqs2_uniref30:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: full_msas_mmseqs2_uniref30
    out: [boltz_yaml]

  predict_full_mmseqs2_uniref30:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_full_mmseqs2_uniref30/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_full_mmseqs2_uniref30:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: predict_full_mmseqs2_uniref30/predicted_cif
    out: [metrics_json]

  # =========================================================================
  # MMseqs2 × UniRef90 — Depth sweep
  # =========================================================================
  subsample_mmseqs2_uniref90:
    run: ../tools/subsample-msa.cwl
    scatter: [msa_a3m, target_depth]
    scatterMethod: flat_crossproduct
    in:
      msa_a3m: full_msas_mmseqs2_uniref90
      target_depth: msa_depths
      random_seed:
        default: 42
    out: [subsampled_a3m]

  make_yaml_mmseqs2_uniref90:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: subsample_mmseqs2_uniref90/subsampled_a3m
    out: [boltz_yaml]

  predict_mmseqs2_uniref90:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_mmseqs2_uniref90/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_mmseqs2_uniref90:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: expand_pdbs/expanded_pdbs
      predicted: predict_mmseqs2_uniref90/predicted_cif
    out: [metrics_json]

  # MMseqs2 × UniRef90 — Full depth
  make_yaml_full_mmseqs2_uniref90:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: full_msas_mmseqs2_uniref90
    out: [boltz_yaml]

  predict_full_mmseqs2_uniref90:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_full_mmseqs2_uniref90/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_full_mmseqs2_uniref90:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: predict_full_mmseqs2_uniref90/predicted_cif
    out: [metrics_json]

  # =========================================================================
  # JackHMMER × UniRef30 — Depth sweep
  # =========================================================================
  subsample_jackhmmer_uniref30:
    run: ../tools/subsample-msa.cwl
    scatter: [msa_a3m, target_depth]
    scatterMethod: flat_crossproduct
    in:
      msa_a3m: full_msas_jackhmmer_uniref30
      target_depth: msa_depths
      random_seed:
        default: 42
    out: [subsampled_a3m]

  make_yaml_jackhmmer_uniref30:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: subsample_jackhmmer_uniref30/subsampled_a3m
    out: [boltz_yaml]

  predict_jackhmmer_uniref30:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_jackhmmer_uniref30/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_jackhmmer_uniref30:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: expand_pdbs/expanded_pdbs
      predicted: predict_jackhmmer_uniref30/predicted_cif
    out: [metrics_json]

  # JackHMMER × UniRef30 — Full depth
  make_yaml_full_jackhmmer_uniref30:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: full_msas_jackhmmer_uniref30
    out: [boltz_yaml]

  predict_full_jackhmmer_uniref30:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_full_jackhmmer_uniref30/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_full_jackhmmer_uniref30:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: predict_full_jackhmmer_uniref30/predicted_cif
    out: [metrics_json]

  # =========================================================================
  # JackHMMER × UniRef90 — Depth sweep
  # =========================================================================
  subsample_jackhmmer_uniref90:
    run: ../tools/subsample-msa.cwl
    scatter: [msa_a3m, target_depth]
    scatterMethod: flat_crossproduct
    in:
      msa_a3m: full_msas_jackhmmer_uniref90
      target_depth: msa_depths
      random_seed:
        default: 42
    out: [subsampled_a3m]

  make_yaml_jackhmmer_uniref90:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: subsample_jackhmmer_uniref90/subsampled_a3m
    out: [boltz_yaml]

  predict_jackhmmer_uniref90:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_jackhmmer_uniref90/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_jackhmmer_uniref90:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: expand_pdbs/expanded_pdbs
      predicted: predict_jackhmmer_uniref90/predicted_cif
    out: [metrics_json]

  # JackHMMER × UniRef90 — Full depth
  make_yaml_full_jackhmmer_uniref90:
    run: ../tools/make-boltz-yaml.cwl
    scatter: msa_file
    in:
      msa_file: full_msas_jackhmmer_uniref90
    out: [boltz_yaml]

  predict_full_jackhmmer_uniref90:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml: make_yaml_full_jackhmmer_uniref90/boltz_yaml
      use_msa_server:
        default: false
      recycling_steps:
        default: 3
    out: [predicted_cif]

  compare_full_jackhmmer_uniref90:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: predict_full_jackhmmer_uniref90/predicted_cif
    out: [metrics_json]

outputs:
  # MMseqs2 × UniRef30
  mmseqs2_uniref30_depth_metrics:
    type: File[]
    outputSource: compare_mmseqs2_uniref30/metrics_json
    doc: "Depth-sweep metrics (MMseqs2/UniRef30), flat array of targets×depths"

  mmseqs2_uniref30_full_metrics:
    type: File[]
    outputSource: compare_full_mmseqs2_uniref30/metrics_json
    doc: "Full-depth metrics (MMseqs2/UniRef30)"

  # MMseqs2 × UniRef90
  mmseqs2_uniref90_depth_metrics:
    type: File[]
    outputSource: compare_mmseqs2_uniref90/metrics_json
    doc: "Depth-sweep metrics (MMseqs2/UniRef90), flat array of targets×depths"

  mmseqs2_uniref90_full_metrics:
    type: File[]
    outputSource: compare_full_mmseqs2_uniref90/metrics_json
    doc: "Full-depth metrics (MMseqs2/UniRef90)"

  # JackHMMER × UniRef30
  jackhmmer_uniref30_depth_metrics:
    type: File[]
    outputSource: compare_jackhmmer_uniref30/metrics_json
    doc: "Depth-sweep metrics (JackHMMER/UniRef30), flat array of targets×depths"

  jackhmmer_uniref30_full_metrics:
    type: File[]
    outputSource: compare_full_jackhmmer_uniref30/metrics_json
    doc: "Full-depth metrics (JackHMMER/UniRef30)"

  # JackHMMER × UniRef90
  jackhmmer_uniref90_depth_metrics:
    type: File[]
    outputSource: compare_jackhmmer_uniref90/metrics_json
    doc: "Depth-sweep metrics (JackHMMER/UniRef90), flat array of targets×depths"

  jackhmmer_uniref90_full_metrics:
    type: File[]
    outputSource: compare_full_jackhmmer_uniref90/metrics_json
    doc: "Full-depth metrics (JackHMMER/UniRef90)"

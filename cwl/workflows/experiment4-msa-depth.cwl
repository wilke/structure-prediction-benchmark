cwlVersion: v1.2
class: Workflow
label: "Experiment 4: MSA Depth Sensitivity Analysis"
doc: |
  Determines optimal MSA depth by subsampling MSAs to various sizes
  and measuring prediction quality at each depth level.

  For each target × MSA source × depth level:
    1. Subsample MSA to target depth
    2. Run Boltz prediction with subsampled MSA
    3. Compare to experimental structure

  MSA depths: 1 (single-seq), 8, 16, 32, 64, 128, 256, 512, 1024, full
  MSA sources: MMseqs2, JackHMMER

  Produces learning curves: quality metric vs MSA depth.

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

  full_msas_mmseqs2:
    type: File[]
    doc: "Full MSAs from MMseqs2 (A3M format)"

  full_msas_jackhmmer:
    type: File[]
    doc: "Full MSAs from JackHMMER (A3M format)"

  msa_depths:
    type: int[]
    default: [1, 8, 16, 32, 64, 128, 256, 512, 1024]
    doc: "MSA depth levels to test (excluding 'full')"

steps:
  # --- Subworkflow: test one MSA source at all depths for one target ---
  depth_sweep_mmseqs2:
    doc: "Sweep MSA depths using MMseqs2 MSAs for each target"
    run:
      class: Workflow
      requirements:
        ScatterFeatureRequirement: {}
      inputs:
        full_msa:
          type: File
        experimental_pdb:
          type: File
        depths:
          type: int[]
      steps:
        subsample:
          run: ../tools/subsample-msa.cwl
          scatter: target_depth
          in:
            msa_a3m: full_msa
            target_depth: depths
            random_seed:
              default: 42
          out: [subsampled_a3m]

        # Generate Boltz YAML for each subsampled MSA
        make_boltz_yaml:
          run:
            class: CommandLineTool
            baseCommand: ["python", "-c"]
            hints:
              DockerRequirement:
                dockerPull: "python:3.11-slim"
            requirements:
              InlineJavascriptRequirement: {}
            arguments:
              - position: 0
                valueFrom: |
                  import sys, yaml
                  msa_path = sys.argv[1]
                  # Read query sequence from A3M
                  with open(msa_path) as f:
                      header = f.readline().strip()
                      seq = ''
                      for line in f:
                          if line.startswith('>'):
                              break
                          seq += line.strip()
                  config = {
                      'sequences': [{
                          'id': 'A',
                          'entity_type': 'protein',
                          'sequence': seq,
                          'msa': msa_path
                      }]
                  }
                  with open('input.yaml', 'w') as f:
                      yaml.dump(config, f)
            inputs:
              msa_file:
                type: File
                inputBinding:
                  position: 1
            outputs:
              boltz_yaml:
                type: File
                outputBinding:
                  glob: "input.yaml"
          scatter: msa_file
          in:
            msa_file: subsample/subsampled_a3m
          out: [boltz_yaml]

        predict:
          run: ../tools/boltz-predict.cwl
          scatter: input_yaml
          in:
            input_yaml: make_boltz_yaml/boltz_yaml
            use_msa_server:
              default: false
            recycling_steps:
              default: 3
          out: [predicted_cif]

        compare:
          run: ../tools/compare-structures.cwl
          scatter: predicted
          in:
            reference: experimental_pdb
            predicted: predict/predicted_cif
          out: [metrics_json]

      outputs:
        depth_metrics:
          type: File[]
          outputSource: compare/metrics_json
    scatter: [full_msa, experimental_pdb]
    scatterMethod: dotproduct
    in:
      full_msa: full_msas_mmseqs2
      experimental_pdb: experimental_pdbs
      depths: msa_depths
    out: [depth_metrics]

  # --- Same sweep for JackHMMER MSAs ---
  depth_sweep_jackhmmer:
    doc: "Sweep MSA depths using JackHMMER MSAs for each target"
    run:
      class: Workflow
      requirements:
        ScatterFeatureRequirement: {}
      inputs:
        full_msa:
          type: File
        experimental_pdb:
          type: File
        depths:
          type: int[]
      steps:
        subsample:
          run: ../tools/subsample-msa.cwl
          scatter: target_depth
          in:
            msa_a3m: full_msa
            target_depth: depths
            random_seed:
              default: 42
          out: [subsampled_a3m]

        make_boltz_yaml:
          run:
            class: CommandLineTool
            baseCommand: ["python", "-c"]
            hints:
              DockerRequirement:
                dockerPull: "python:3.11-slim"
            requirements:
              InlineJavascriptRequirement: {}
            arguments:
              - position: 0
                valueFrom: |
                  import sys, yaml
                  msa_path = sys.argv[1]
                  with open(msa_path) as f:
                      header = f.readline().strip()
                      seq = ''
                      for line in f:
                          if line.startswith('>'):
                              break
                          seq += line.strip()
                  config = {
                      'sequences': [{
                          'id': 'A',
                          'entity_type': 'protein',
                          'sequence': seq,
                          'msa': msa_path
                      }]
                  }
                  with open('input.yaml', 'w') as f:
                      yaml.dump(config, f)
            inputs:
              msa_file:
                type: File
                inputBinding:
                  position: 1
            outputs:
              boltz_yaml:
                type: File
                outputBinding:
                  glob: "input.yaml"
          scatter: msa_file
          in:
            msa_file: subsample/subsampled_a3m
          out: [boltz_yaml]

        predict:
          run: ../tools/boltz-predict.cwl
          scatter: input_yaml
          in:
            input_yaml: make_boltz_yaml/boltz_yaml
            use_msa_server:
              default: false
            recycling_steps:
              default: 3
          out: [predicted_cif]

        compare:
          run: ../tools/compare-structures.cwl
          scatter: predicted
          in:
            reference: experimental_pdb
            predicted: predict/predicted_cif
          out: [metrics_json]

      outputs:
        depth_metrics:
          type: File[]
          outputSource: compare/metrics_json
    scatter: [full_msa, experimental_pdb]
    scatterMethod: dotproduct
    in:
      full_msa: full_msas_jackhmmer
      experimental_pdb: experimental_pdbs
      depths: msa_depths
    out: [depth_metrics]

  # --- Full-depth predictions (no subsampling) ---
  boltz_full_mmseqs2:
    run: ../tools/boltz-predict.cwl
    scatter: input_yaml
    in:
      input_yaml:
        # These would be Boltz YAMLs with full MMseqs2 MSAs
        source: full_msas_mmseqs2
      use_msa_server:
        default: false
    out: [predicted_cif]

  compare_full_mmseqs2:
    run: ../tools/compare-structures.cwl
    scatter: [reference, predicted]
    scatterMethod: dotproduct
    in:
      reference: experimental_pdbs
      predicted: boltz_full_mmseqs2/predicted_cif
    out: [metrics_json]

outputs:
  mmseqs2_depth_metrics:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: depth_sweep_mmseqs2/depth_metrics
    doc: "Per-target array of per-depth metrics (MMseqs2)"

  jackhmmer_depth_metrics:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: depth_sweep_jackhmmer/depth_metrics
    doc: "Per-target array of per-depth metrics (JackHMMER)"

  full_depth_metrics:
    type: File[]
    outputSource: compare_full_mmseqs2/metrics_json
    doc: "Full-depth MSA prediction metrics"

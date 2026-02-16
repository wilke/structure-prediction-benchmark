cwlVersion: v1.2
class: Workflow
label: "Experiment 2: Cross-Tool Comparison"
doc: |
  For each target protein, performs all-vs-all pairwise comparison of
  predicted structures from different tools (AF2, Boltz, Chai, ESMFold)
  plus comparison against the experimental reference.

  Produces a pairwise metrics matrix for each target showing agreement
  and disagreement between prediction tools.

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}
  InlineJavascriptRequirement: {}
  MultipleInputFeatureRequirement: {}

inputs:
  # Per-target arrays (all same length, matched by index)
  target_ids:
    type: string[]
    doc: "Target protein identifiers"

  experimental_pdbs:
    type: File[]
    doc: "Experimental reference structures"

  alphafold_pdbs:
    type: File[]
    doc: "AlphaFold2 predicted structures (from Experiment 1)"

  boltz_cifs:
    type: File[]
    doc: "Boltz predicted structures (from Experiment 1)"

  chai_cifs:
    type: File[]
    doc: "Chai predicted structures (from Experiment 1)"

  esmfold_pdbs:
    type: File[]
    doc: "ESMFold predicted structures (from Experiment 1)"

steps:
  # Batch comparison: all tools + experimental for each target
  # Each batch includes: experimental, AF2, Boltz, Chai, ESM
  batch_compare:
    run:
      class: CommandLineTool
      baseCommand: ["python", "-m", "protein_compare", "batch"]
      hints:
        DockerRequirement:
          dockerPull: "dxkb/protein-compare:latest"
      requirements:
        InlineJavascriptRequirement: {}
      arguments:
        - prefix: "-o"
          valueFrom: "cross_tool_metrics.csv"
      inputs:
        experimental:
          type: File
          inputBinding:
            position: 1
        alphafold:
          type: File
          inputBinding:
            position: 2
        boltz:
          type: File
          inputBinding:
            position: 3
        chai:
          type: File
          inputBinding:
            position: 4
        esmfold:
          type: File
          inputBinding:
            position: 5
        ref:
          type: File
          inputBinding:
            prefix: "--reference"
      outputs:
        metrics_csv:
          type: File
          outputBinding:
            glob: "cross_tool_metrics.csv"
    scatter: [experimental, alphafold, boltz, chai, esmfold, ref]
    scatterMethod: dotproduct
    in:
      experimental: experimental_pdbs
      alphafold: alphafold_pdbs
      boltz: boltz_cifs
      chai: chai_cifs
      esmfold: esmfold_pdbs
      ref: experimental_pdbs
    out: [metrics_csv]

outputs:
  cross_tool_metrics:
    type: File[]
    outputSource: batch_compare/metrics_csv
    doc: "Per-target pairwise comparison CSV (all tools vs reference)"

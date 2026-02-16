cwlVersion: v1.2
class: CommandLineTool
label: ESMFold structure prediction (single-sequence baseline)
doc: |
  Runs ESMFold protein structure prediction using Docker.
  Single-sequence model — no MSA required or supported.
  Serves as a baseline for MSA impact comparison.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/esmfold:latest"
  DockerRequirement:
    dockerPull: "dxkb/esmfold:latest"
  ResourceRequirement:
    coresMin: 4
    ramMin: 16000

baseCommand: ["esm-fold"]

arguments:
  - prefix: "-o"
    valueFrom: $(runtime.outdir)

inputs:
  fasta:
    type: File
    inputBinding:
      prefix: "-i"
    doc: "Input FASTA file with target sequence"

  num_recycles:
    type: int
    default: 4
    inputBinding:
      prefix: "--num-recycles"
    doc: "Number of refinement recycles (default: 4)"

  max_tokens_per_batch:
    type: int
    default: 1024
    inputBinding:
      prefix: "--max-tokens-per-batch"
    doc: "Max tokens per GPU batch"

  chunk_size:
    type: int?
    inputBinding:
      prefix: "--chunk-size"
    doc: "Axial attention chunk size for memory optimization"

outputs:
  predicted_pdb:
    type: File
    outputBinding:
      glob: "*.pdb"
    doc: "Predicted structure in PDB format with pLDDT in B-factor"

cwlVersion: v1.2
class: CommandLineTool
label: Chai structure prediction
doc: |
  Runs Chai protein structure prediction using Docker.
  Supports precomputed MSAs or single-sequence mode.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/chai-bvbrc:latest-gpu"
  DockerRequirement:
    dockerPull: "dxkb/chai-bvbrc:latest-gpu"
  ResourceRequirement:
    coresMin: 4
    ramMin: 16000

baseCommand: ["chai"]

arguments:
  - prefix: "--output-dir"
    valueFrom: $(runtime.outdir)

inputs:
  fasta:
    type: File
    inputBinding:
      prefix: "--fasta"
    doc: "Input FASTA file with target sequence"

  msa_file:
    type: File?
    inputBinding:
      prefix: "--msa"
    doc: "Precomputed MSA file (.aligned.pqt Parquet format). Use a3m-to-pqt.cwl to convert from A3M. Omit for single-sequence mode."

  num_models:
    type: int
    default: 1
    inputBinding:
      prefix: "--num-models"
    doc: "Number of model predictions to generate"

  use_msa_server:
    type: boolean
    default: false
    inputBinding:
      prefix: "--use-msa-server"
    doc: "Auto-generate MSAs via remote server"

outputs:
  predicted_cif:
    type: File
    outputBinding:
      glob: "**/pred.model_idx_0.cif"
    doc: "Best predicted structure (mmCIF)"

  all_cifs:
    type: File[]
    outputBinding:
      glob: "**/pred.model_idx_*.cif"
    doc: "All predicted structures"

  scores_json:
    type: File
    outputBinding:
      glob: "**/scores.model_idx_0.npz"
    doc: "Prediction confidence scores"

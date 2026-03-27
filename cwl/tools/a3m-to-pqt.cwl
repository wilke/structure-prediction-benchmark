cwlVersion: v1.2
class: CommandLineTool
label: Convert A3M MSA to Chai aligned Parquet format
doc: |
  Converts an A3M-format multiple sequence alignment to the .aligned.pqt
  (Parquet) format required by Chai for precomputed MSA input.

  Chai does not accept A3M directly — it requires a Parquet dataframe with
  columns: sequence, source_database, pairing_key, comment.

  This tool uses the chai CLI's built-in a3m-to-pqt converter.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/chai:latest"
  DockerRequirement:
    dockerPull: "dxkb/chai:latest"
  ResourceRequirement:
    coresMin: 1
    ramMin: 4000

baseCommand: ["chai", "a3m-to-pqt"]

inputs:
  a3m_file:
    type: File
    inputBinding:
      prefix: "--input"
    doc: "Input MSA in A3M format"

  output_name:
    type: string
    default: "alignment.aligned.pqt"
    inputBinding:
      prefix: "--output"
    doc: "Output filename for the Parquet MSA"

outputs:
  pqt_file:
    type: File
    outputBinding:
      glob: "*.aligned.pqt"
    doc: "MSA in Chai's aligned Parquet format"

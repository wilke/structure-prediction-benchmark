cwlVersion: v1.2
class: CommandLineTool
label: MSA generation via JackHMMER
doc: |
  Generates multiple sequence alignments using JackHMMER iterative
  search against UniRef90. This is the AlphaFold2 native MSA method.

hints:
  goweHint:
    executor: local
    docker_image: "staphb/hmmer:latest"
  DockerRequirement:
    dockerPull: "staphb/hmmer:latest"
  ResourceRequirement:
    coresMin: 8
    ramMin: 32000

baseCommand: ["jackhmmer"]

arguments:
  - prefix: "-A"
    valueFrom: $(runtime.outdir)/output.sto
  - prefix: "-o"
    valueFrom: $(runtime.outdir)/output.log

inputs:
  fasta:
    type: File
    inputBinding:
      position: 1
    doc: "Query FASTA file"

  database:
    type: File
    inputBinding:
      position: 2
    doc: "Target sequence database (e.g., UniRef90)"

  iterations:
    type: int
    default: 3
    inputBinding:
      prefix: "-N"
    doc: "Number of iterative search rounds"

  evalue:
    type: float
    default: 0.0001
    inputBinding:
      prefix: "-E"
    doc: "E-value inclusion threshold"

  incE:
    type: float
    default: 0.0001
    inputBinding:
      prefix: "--incE"
    doc: "Per-domain inclusion E-value"

  cpus:
    type: int
    default: 8
    inputBinding:
      prefix: "--cpu"
    doc: "Number of CPU threads"

outputs:
  msa_sto:
    type: File
    outputBinding:
      glob: "output.sto"
    doc: "Output MSA in Stockholm format"

  search_log:
    type: File
    outputBinding:
      glob: "output.log"
    doc: "JackHMMER search log"

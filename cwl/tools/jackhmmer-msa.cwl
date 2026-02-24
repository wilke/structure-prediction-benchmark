cwlVersion: v1.2
class: CommandLineTool
label: MSA generation via JackHMMER
doc: |
  Generates multiple sequence alignments using JackHMMER iterative
  search against a protein sequence database. Outputs Stockholm format
  MSA and search log.

requirements:
  InlineJavascriptRequirement: {}

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
    valueFrom: $(runtime.outdir)/$(inputs.output_prefix).sto
  - prefix: "-o"
    valueFrom: $(runtime.outdir)/$(inputs.output_prefix).log

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
    doc: "Target sequence database (e.g., UniRef90 FASTA)"

  output_prefix:
    type: string
    default: "output"
    doc: "Prefix for output filenames (e.g., 1ubq_chainA.jackhmmer.uniref90)"

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
      glob: "*.sto"
    doc: "Output MSA in Stockholm format"

  search_log:
    type: File
    outputBinding:
      glob: "*.log"
    doc: "JackHMMER search log"

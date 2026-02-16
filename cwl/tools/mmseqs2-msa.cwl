cwlVersion: v1.2
class: CommandLineTool
label: MSA generation via MMseqs2
doc: |
  Generates multiple sequence alignments using MMseqs2 against
  ColabFold databases. Fast and broad coverage.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/mmseqs2:latest"
  DockerRequirement:
    dockerPull: "dxkb/mmseqs2:latest"
  ResourceRequirement:
    coresMin: 8
    ramMin: 32000

baseCommand: ["mmseqs", "easy-search"]

arguments:
  - valueFrom: $(runtime.outdir)/result
    position: 3
  - valueFrom: $(runtime.outdir)/tmp
    position: 4
  - prefix: "--format-mode"
    valueFrom: "5"
  - prefix: "--format-output"
    valueFrom: "query,target,qseq,tseq,qaln,taln,evalue,bits"

inputs:
  fasta:
    type: File
    inputBinding:
      position: 1
    doc: "Query FASTA file"

  database:
    type: Directory
    inputBinding:
      position: 2
    doc: "MMseqs2 database directory"

  sensitivity:
    type: float
    default: 7.5
    inputBinding:
      prefix: "-s"
    doc: "Sensitivity (1-8, higher = more sensitive but slower)"

  max_seqs:
    type: int
    default: 10000
    inputBinding:
      prefix: "--max-seqs"
    doc: "Maximum number of sequences to retain"

  evalue:
    type: float
    default: 0.001
    inputBinding:
      prefix: "-e"
    doc: "E-value threshold"

  threads:
    type: int
    default: 8
    inputBinding:
      prefix: "--threads"
    doc: "Number of CPU threads"

outputs:
  msa_a3m:
    type: File
    outputBinding:
      glob: "result.a3m"
    doc: "Output MSA in A3M format"

  search_results:
    type: File?
    outputBinding:
      glob: "result.m8"
    doc: "Search results in tabular format"

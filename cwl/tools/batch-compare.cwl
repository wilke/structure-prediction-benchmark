cwlVersion: v1.2
class: CommandLineTool
label: Batch protein structure comparison
doc: |
  Performs batch pairwise comparison of multiple predicted structures,
  optionally against a reference (experimental) structure.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/protein-compare:latest"
  DockerRequirement:
    dockerPull: "dxkb/protein-compare:latest"
  ResourceRequirement:
    coresMin: 4
    ramMin: 8000

baseCommand: ["python", "-m", "protein_compare", "batch"]

arguments:
  - prefix: "-o"
    valueFrom: "batch_metrics.csv"

inputs:
  structures:
    type: File[]
    inputBinding:
      position: 1
    doc: "Array of structure files to compare pairwise"

  reference:
    type: File?
    inputBinding:
      prefix: "--reference"
    doc: "Optional reference structure (all-vs-reference mode)"

  parallel_jobs:
    type: int
    default: -1
    inputBinding:
      prefix: "-j"
    doc: "Number of parallel comparison jobs (-1 = all CPUs)"

outputs:
  metrics_csv:
    type: File
    outputBinding:
      glob: "batch_metrics.csv"
    doc: |
      Pairwise comparison metrics CSV with columns:
      structure_1, structure_2, tm_score, rmsd, weighted_rmsd,
      aligned_length, seq_identity, gdt_ts, gdt_ha,
      ss_agreement, contact_jaccard, mean_plddt_1, mean_plddt_2,
      n_divergent_residues

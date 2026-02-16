cwlVersion: v1.2
class: CommandLineTool
label: Protein structure comparison
doc: |
  Compares predicted protein structures against a reference (experimental)
  structure using the protein_compare tool. Computes TM-score, RMSD,
  GDT-TS, GDT-HA, contact Jaccard, and secondary structure agreement.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/protein-compare:latest"
  DockerRequirement:
    dockerPull: "dxkb/protein-compare:latest"
  ResourceRequirement:
    coresMin: 2
    ramMin: 4000

baseCommand: ["python", "-m", "protein_compare", "compare"]

inputs:
  reference:
    type: File
    inputBinding:
      position: 1
    doc: "Reference (experimental) structure file (PDB/CIF)"

  predicted:
    type: File
    inputBinding:
      position: 2
    doc: "Predicted structure file (PDB/CIF)"

  output_format:
    type:
      type: enum
      symbols: ["json", "csv"]
    default: "json"
    inputBinding:
      prefix: "--output"
      valueFrom: |
        ${
          if (self === "json") return "metrics.json";
          return "metrics.csv";
        }
    doc: "Output format for metrics"

  pymol_script:
    type: boolean
    default: true
    inputBinding:
      prefix: "--pymol"
      valueFrom: "alignment.pml"
    doc: "Generate PyMOL alignment script"

  divergence_plot:
    type: boolean
    default: true
    inputBinding:
      prefix: "--plot"
      valueFrom: "divergence.png"
    doc: "Generate divergence plot"

outputs:
  metrics_json:
    type: File?
    outputBinding:
      glob: "metrics.json"
    doc: "Comparison metrics in JSON format"

  metrics_csv:
    type: File?
    outputBinding:
      glob: "metrics.csv"
    doc: "Comparison metrics in CSV format"

  alignment_pml:
    type: File?
    outputBinding:
      glob: "alignment.pml"
    doc: "PyMOL visualization script"

  divergence_plot:
    type: File?
    outputBinding:
      glob: "divergence.png"
    doc: "Per-residue divergence plot"

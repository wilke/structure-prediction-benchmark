cwlVersion: v1.2
class: CommandLineTool
label: AlphaFold2 structure prediction
doc: |
  Runs AlphaFold2 protein structure prediction using Docker.
  Supports precomputed MSAs or generates them internally.

hints:
  goweHint:
    executor: local
    docker_image: "wilke/alphafold:latest"
  DockerRequirement:
    dockerPull: "wilke/alphafold:latest"
  ResourceRequirement:
    coresMin: 8
    ramMin: 16000

baseCommand: ["python", "/app/alphafold/run_alphafold.py"]

arguments:
  - prefix: "--output_dir"
    valueFrom: $(runtime.outdir)

inputs:
  fasta:
    type: File
    inputBinding:
      prefix: "--fasta_paths"
    doc: "Input FASTA file with target sequence"

  data_dir:
    type: Directory
    inputBinding:
      prefix: "--data_dir"
    doc: "Path to AlphaFold genetic databases"

  model_preset:
    type:
      type: enum
      symbols: ["monomer", "monomer_casp14", "monomer_ptm", "multimer"]
    default: "monomer"
    inputBinding:
      prefix: "--model_preset"
    doc: "Model configuration preset"

  db_preset:
    type:
      type: enum
      symbols: ["full_dbs", "reduced_dbs"]
    default: "full_dbs"
    inputBinding:
      prefix: "--db_preset"
    doc: "Database preset (full or reduced)"

  use_precomputed_msas:
    type: boolean
    default: false
    inputBinding:
      prefix: "--use_precomputed_msas"
      valueFrom: $(self ? "true" : "false")
    doc: "Use precomputed MSAs from a previous run"

  max_template_date:
    type: string
    default: "1900-01-01"
    inputBinding:
      prefix: "--max_template_date"
    doc: "Maximum template release date (YYYY-MM-DD). Set to 1900-01-01 to disable templates and isolate MSA effects."

  msa_dir:
    type: Directory?
    inputBinding:
      prefix: "--msa_dir"
    doc: "Directory with precomputed MSAs (when use_precomputed_msas=true). Must contain A3M/STO files in {target_name}/msas/ subdirectory structure."

outputs:
  predicted_pdb:
    type: File
    outputBinding:
      glob: "*/ranked_0.pdb"
    doc: "Best-ranked predicted structure"

  all_pdbs:
    type: File[]
    outputBinding:
      glob: "*/ranked_*.pdb"
    doc: "All ranked predicted structures"

  ranking_json:
    type: File
    outputBinding:
      glob: "*/ranking_debug.json"
    doc: "Model ranking and pLDDT scores"

  timings_json:
    type: File
    outputBinding:
      glob: "*/timings.json"
    doc: "Pipeline execution timings"

  msas_dir:
    type: Directory?
    outputBinding:
      glob: "*/msas"
    doc: "Generated MSA directory (for reuse)"

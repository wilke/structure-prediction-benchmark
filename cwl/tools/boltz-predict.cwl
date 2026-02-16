cwlVersion: v1.2
class: CommandLineTool
label: Boltz structure prediction
doc: |
  Runs Boltz protein structure prediction using Docker.
  Supports precomputed MSAs (A3M) or auto-generation via MMseqs2 server.

hints:
  goweHint:
    executor: local
    docker_image: "dxkb/boltz:latest"
  DockerRequirement:
    dockerPull: "dxkb/boltz:latest"
  ResourceRequirement:
    coresMin: 4
    ramMin: 16000

baseCommand: ["boltz", "predict"]

arguments:
  - prefix: "--out_dir"
    valueFrom: $(runtime.outdir)

inputs:
  input_yaml:
    type: File
    inputBinding:
      position: 1
    doc: "Boltz YAML input file defining sequences and optional MSA paths"

  use_msa_server:
    type: boolean
    default: false
    inputBinding:
      prefix: "--use_msa_server"
    doc: "Auto-generate MSAs via MMseqs2 server"

  recycling_steps:
    type: int
    default: 3
    inputBinding:
      prefix: "--recycling_steps"
    doc: "Number of iterative refinement steps (1-6)"

  diffusion_samples:
    type: int
    default: 1
    inputBinding:
      prefix: "--diffusion_samples"
    doc: "Number of diffusion samples to generate"

  use_potentials:
    type: boolean
    default: false
    inputBinding:
      prefix: "--use_potentials"
    doc: "Apply Boltz-Steering potentials for physical plausibility"

outputs:
  predicted_cif:
    type: File
    outputBinding:
      glob: "predictions/*/*_model_0.cif"
    doc: "Best-ranked predicted structure (mmCIF)"

  all_cifs:
    type: File[]
    outputBinding:
      glob: "predictions/*/*_model_*.cif"
    doc: "All predicted structures"

  confidence_json:
    type: File
    outputBinding:
      glob: "predictions/*/confidence_*_model_0.json"
    doc: "Confidence scores (pTM, ipTM, pLDDT)"

  plddt_npz:
    type: File
    outputBinding:
      glob: "predictions/*/plddt_*_model_0.npz"
    doc: "Per-residue pLDDT scores"

  pae_npz:
    type: File?
    outputBinding:
      glob: "predictions/*/pae_*_model_0.npz"
    doc: "Predicted aligned error matrix"

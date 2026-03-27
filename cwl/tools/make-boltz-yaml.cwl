cwlVersion: v1.2
class: CommandLineTool
label: Generate Boltz input YAML from A3M MSA
doc: |
  Reads the query sequence from an A3M MSA file and writes a Boltz-format
  input YAML referencing that MSA. Used to bridge subsample-msa output
  to boltz-predict input.

requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - $(inputs.msa_file)

hints:
  goweHint:
    executor: local
    docker_image: "python:3.11-slim"
  DockerRequirement:
    dockerPull: "python:3.11-slim"

baseCommand: ["python", "-c"]

arguments:
  - position: 0
    valueFrom: |
      import sys, os

      msa_path = sys.argv[1]

      # Read query sequence from A3M (first entry)
      with open(msa_path) as f:
          header = f.readline().strip()
          seq = ''
          for line in f:
              if line.startswith('>'):
                  break
              seq += line.strip()

      # Strip gap characters from query sequence (A3M alignment artifacts)
      seq = seq.replace('-', '').replace('.', '')

      if not seq:
          sys.exit('Error: could not extract query sequence from A3M')

      # Write Boltz YAML manually (no PyYAML dependency needed)
      with open('input.yaml', 'w') as f:
          f.write('sequences:\n')
          f.write('  - id: A\n')
          f.write('    entity_type: protein\n')
          f.write('    sequence: ' + seq + '\n')
          f.write('    msa: ' + msa_path + '\n')

      print(f'Created Boltz YAML: query length={len(seq)}, msa={msa_path}')

inputs:
  msa_file:
    type: File
    inputBinding:
      position: 1
    doc: "Input MSA in A3M format"

outputs:
  boltz_yaml:
    type: File
    outputBinding:
      glob: "input.yaml"
    doc: "Boltz input YAML with sequence and MSA path"

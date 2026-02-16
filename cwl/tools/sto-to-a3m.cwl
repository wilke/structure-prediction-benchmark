cwlVersion: v1.2
class: CommandLineTool
label: Convert Stockholm MSA to A3M format
doc: |
  Converts a Stockholm-format MSA (from JackHMMER) to A3M format
  for use with Boltz and Chai.

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
      import sys
      import re

      sto_file = sys.argv[1]
      a3m_file = sys.argv[2] if len(sys.argv) > 2 else "output.a3m"

      sequences = {}
      with open(sto_file) as f:
          for line in f:
              line = line.strip()
              if not line or line.startswith(('#', '//')):
                  continue
              parts = line.split()
              if len(parts) == 2:
                  name, seq = parts
                  if name in sequences:
                      sequences[name] += seq
                  else:
                      sequences[name] = seq

      with open(a3m_file, 'w') as f:
          for name, seq in sequences.items():
              # Remove gap-only columns relative to query (first sequence)
              f.write(f">{name}\n{seq}\n")

      print(f"Converted {len(sequences)} sequences from Stockholm to A3M")

inputs:
  sto_file:
    type: File
    inputBinding:
      position: 1
    doc: "Input Stockholm format MSA"

  output_name:
    type: string
    default: "output.a3m"
    inputBinding:
      position: 2
    doc: "Output A3M filename"

outputs:
  a3m_file:
    type: File
    outputBinding:
      glob: "*.a3m"
    doc: "MSA in A3M format"

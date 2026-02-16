cwlVersion: v1.2
class: CommandLineTool
label: Subsample MSA to target depth
doc: |
  Subsamples an A3M multiple sequence alignment to a target number
  of sequences. Used for MSA depth sensitivity experiments.
  Preserves the query sequence as the first entry.

requirements:
  InlineJavascriptRequirement: {}

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
      import random
      import sys

      input_a3m = sys.argv[1]
      target_depth = int(sys.argv[2])
      output_a3m = sys.argv[3]
      seed = int(sys.argv[4]) if len(sys.argv) > 4 else 42

      # Parse A3M: entries are pairs of header + sequence lines
      entries = []
      with open(input_a3m) as f:
          header = None
          seq_lines = []
          for line in f:
              line = line.rstrip()
              if line.startswith('>'):
                  if header is not None:
                      entries.append((header, ''.join(seq_lines)))
                  header = line
                  seq_lines = []
              else:
                  seq_lines.append(line)
          if header is not None:
              entries.append((header, ''.join(seq_lines)))

      if not entries:
          sys.exit("Error: empty MSA file")

      # First entry is query — always kept
      query = entries[0]
      rest = entries[1:]

      # Subsample
      random.seed(seed)
      if target_depth <= 1:
          selected = []  # query only
      elif target_depth - 1 >= len(rest):
          selected = rest  # keep all
      else:
          selected = random.sample(rest, target_depth - 1)

      # Write output
      with open(output_a3m, 'w') as f:
          f.write(query[0] + '\n' + query[1] + '\n')
          for hdr, seq in selected:
              f.write(hdr + '\n' + seq + '\n')

      total = 1 + len(selected)
      print(f"Subsampled: {len(entries)} -> {total} sequences (target: {target_depth})")

inputs:
  msa_a3m:
    type: File
    inputBinding:
      position: 1
    doc: "Input MSA in A3M format"

  target_depth:
    type: int
    inputBinding:
      position: 2
    doc: "Target number of sequences (including query)"

  output_name:
    type: string
    default: "subsampled.a3m"
    inputBinding:
      position: 3
    doc: "Output filename"

  random_seed:
    type: int
    default: 42
    inputBinding:
      position: 4
    doc: "Random seed for reproducible subsampling"

outputs:
  subsampled_a3m:
    type: File
    outputBinding:
      glob: "subsampled*.a3m"
    doc: "Subsampled MSA in A3M format"

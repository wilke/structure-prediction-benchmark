cwlVersion: v1.2
class: CommandLineTool
label: Fetch experimental structure from RCSB PDB
doc: |
  Downloads an experimental protein structure from RCSB PDB
  and optionally extracts a specific chain.

requirements:
  InlineJavascriptRequirement: {}
  NetworkAccess:
    networkAccess: true

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
      from urllib.request import urlretrieve

      pdb_id = sys.argv[1].lower()
      chain = sys.argv[2] if len(sys.argv) > 2 else None

      url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
      outfile = f"{pdb_id}.pdb"
      print(f"Downloading {url}")
      urlretrieve(url, outfile)

      if chain:
          chain_file = f"{pdb_id}_chain{chain}.pdb"
          with open(outfile) as fin, open(chain_file, 'w') as fout:
              for line in fin:
                  if line.startswith(('ATOM', 'HETATM')):
                      if len(line) > 21 and line[21] == chain:
                          fout.write(line)
                  elif line.startswith('END'):
                      fout.write(line)
          print(f"Extracted chain {chain} -> {chain_file}")

inputs:
  pdb_id:
    type: string
    inputBinding:
      position: 1
    doc: "4-letter PDB identifier"

  chain_id:
    type: string?
    inputBinding:
      position: 2
    doc: "Chain identifier to extract (optional)"

outputs:
  structure_pdb:
    type: File
    outputBinding:
      glob: "*_chain*.pdb"
    doc: "Downloaded/extracted PDB structure"

  full_pdb:
    type: File
    outputBinding:
      glob: "*.pdb"
    doc: "Full PDB file"

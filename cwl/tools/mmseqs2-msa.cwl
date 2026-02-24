cwlVersion: v1.2
class: CommandLineTool
label: MSA generation via MMseqs2
doc: |
  Generates multiple sequence alignments using MMseqs2 against
  a sequence database. Runs search → result2msa pipeline to produce
  A3M-format MSAs. Fast and broad coverage.

requirements:
  InlineJavascriptRequirement: {}
  InitialWorkDirRequirement:
    listing:
      - entryname: run_mmseqs_msa.sh
        entry: |
          #!/bin/sh
          set -e
          FASTA="$1"
          DB_PREFIX="$2"
          SENSITIVITY="$3"
          MAX_SEQS="$4"
          EVALUE="$5"
          THREADS="$6"
          OUTNAME="$7"
          OUTDIR="\$(pwd)"
          TMPDIR="$OUTDIR/tmp"
          mkdir -p "$TMPDIR"

          # Create query DB from FASTA
          mmseqs createdb "$FASTA" "$TMPDIR/queryDB"

          # Search against target database (expects native MMseqs2 DB format)
          mmseqs search "$TMPDIR/queryDB" "$DB_PREFIX" \
            "$TMPDIR/resultDB" "$TMPDIR/search_tmp" \
            -s "$SENSITIVITY" \
            --max-seqs "$MAX_SEQS" \
            -e "$EVALUE" \
            --threads "$THREADS"

          # Convert search results to A3M MSA
          mmseqs result2msa "$TMPDIR/queryDB" "$DB_PREFIX" \
            "$TMPDIR/resultDB" "$TMPDIR/msaDB" \
            --msa-format-mode 6 \
            --threads "$THREADS"

          # Extract A3M from the MSA DB
          mmseqs unpackdb "$TMPDIR/msaDB" "$OUTDIR" --unpack-name-mode 0 --unpack-suffix .a3m

          # Rename the first (only) output to the prefixed name
          mv "$OUTDIR/0.a3m" "$OUTDIR/$OUTNAME" 2>/dev/null || \
            mv "$OUTDIR"/*.a3m "$OUTDIR/$OUTNAME" 2>/dev/null || true

          # Clean up tmp to save space
          rm -rf "$TMPDIR"

hints:
  goweHint:
    executor: local
    docker_image: "staphb/mmseqs2:latest"
  DockerRequirement:
    dockerPull: "staphb/mmseqs2:latest"
  ResourceRequirement:
    coresMin: 8
    ramMin: 32000

baseCommand: ["sh", "run_mmseqs_msa.sh"]

inputs:
  fasta:
    type: File
    inputBinding:
      position: 1
    doc: "Query FASTA file"

  database:
    type: Directory
    doc: "MMseqs2 database directory"

  db_prefix:
    type: string
    default: "uniref30_2302"
    inputBinding:
      position: 2
      valueFrom: $(inputs.database.path + "/" + inputs.db_prefix)
    doc: "Database prefix within the directory (e.g., uniref30_2302)"

  sensitivity:
    type: float
    default: 7.5
    inputBinding:
      position: 3
    doc: "Sensitivity (1-8, higher = more sensitive but slower)"

  max_seqs:
    type: int
    default: 10000
    inputBinding:
      position: 4
    doc: "Maximum number of sequences to retain"

  evalue:
    type: float
    default: 0.001
    inputBinding:
      position: 5
    doc: "E-value threshold"

  threads:
    type: int
    default: 8
    inputBinding:
      position: 6
    doc: "Number of CPU threads"

  output_prefix:
    type: string
    default: "output"
    inputBinding:
      position: 7
      valueFrom: $(inputs.output_prefix).a3m
    doc: "Prefix for output filename (e.g., 1ubq_chainA.mmseqs2.uniref90)"

outputs:
  msa_a3m:
    type: File
    outputBinding:
      glob: "*.a3m"
    doc: "Output MSA in A3M format"

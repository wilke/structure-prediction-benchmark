FROM python:3.11-slim

LABEL maintainer="dxkb"
LABEL description="Protein structure comparison tool (protein_compare) with DSSP support"
LABEL source="https://github.com/BV-BRC/protein_structure_analysis"

# Install system dependencies (DSSP for secondary structure assignment)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        dssp \
        git \
    && rm -rf /var/lib/apt/lists/*

# Ensure mkdssp is available on PATH (some distros install as /usr/bin/mkdssp)
RUN ln -sf /usr/bin/mkdssp /usr/local/bin/mkdssp 2>/dev/null || true

# Install protein_structure_analysis from GitHub
RUN pip install --no-cache-dir \
    "protein_compare @ git+https://github.com/BV-BRC/protein_structure_analysis.git"

# Verify the install
RUN python -m protein_compare --help

WORKDIR /work
ENTRYPOINT ["python", "-m", "protein_compare"]

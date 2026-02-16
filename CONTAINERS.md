# Container Registry

All CWL tools require Docker containers. This document tracks the availability
of each container image and links to their Dockerfiles where applicable.

## Container Status

| CWL Tool | Container Image | Status |
|----------|----------------|--------|
| `alphafold-predict.cwl` | `wilke/alphafold:latest` | Present |
| `boltz-predict.cwl` | `dxkb/boltz:latest` | Present |
| `chai-predict.cwl` | `dxkb/chai:latest` | Present |
| `esmfold-predict.cwl` | `dxkb/esmfold:latest` | Present |
| `compare-structures.cwl` | `dxkb/protein-compare:latest` | Missing — needs build |
| `batch-compare.cwl` | `dxkb/protein-compare:latest` | Missing (same image) |
| `mmseqs2-msa.cwl` | `staphb/mmseqs2:latest` | Present (public) |
| `jackhmmer-msa.cwl` | `staphb/hmmer:latest` | Present (public) |
| `subsample-msa.cwl` | `python:3.11-slim` | Present (official) |
| `sto-to-a3m.cwl` | `python:3.11-slim` | Present (official) |
| `fetch-pdb.cwl` | `python:3.11-slim` | Present (official) |

## Summary

- **8** unique container images required
- **7** present
- **1** missing and needs to be built:
  - `dxkb/protein-compare` — structure comparison ([Dockerfile](docker/protein-compare/Dockerfile))

## Public Container Sources

| Container | Source | Registry |
|-----------|--------|----------|
| `staphb/mmseqs2` | [StaPH-B/docker-builds](https://github.com/StaPH-B/docker-builds) | Docker Hub ([staphb/mmseqs2](https://hub.docker.com/r/staphb/mmseqs2)) |
| `staphb/hmmer` | [StaPH-B/docker-builds](https://github.com/StaPH-B/docker-builds) | Docker Hub ([staphb/hmmer](https://hub.docker.com/r/staphb/hmmer)) |
| `python:3.11-slim` | [python](https://hub.docker.com/_/python) | Docker Hub (official) |

## Custom Container Sources

| Container | Source Code | Dockerfile |
|-----------|------------|------------|
| `dxkb/protein-compare` | [BV-BRC/protein_structure_analysis](https://github.com/BV-BRC/protein_structure_analysis) | [docker/protein-compare/Dockerfile](docker/protein-compare/Dockerfile) |

## Building Missing Containers

```bash
# protein-compare
docker build -t dxkb/protein-compare:latest docker/protein-compare/
docker push dxkb/protein-compare:latest
```

# Third-Party Notices and Attribution

This project uses open-source software and references published research. The following information records the main upstream reference and runtime dependencies.

## SCoPP upstream reference

- Project: *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas*
- Official repository: https://github.com/adamslab-ub/SCoPP
- Repository license: MIT License
- Paper: L. Collins, P. Ghassemi, S. Chowdhury, K. Dantu, E. Esfahani, and D. Doermann, ICRA 2021, arXiv:2103.14709
- Code reference used for parity review: `monitoring_algorithms.py` and `SCoPP_settings.py` from the upstream `main` branch

The present repository keeps SCoPP behavior as a comparison baseline for clustering, conflict-cell auction, and `paper_nn`, while adding project-specific indoor planning features.

Project-specific extensions include:

- indoor Cartesian map and boundary policies;
- no-fly-zone geometry and valid-cell executable routing;
- metric closure over the 4-neighbor valid-cell graph;
- deterministic cheapest insertion plus 2-opt under `approx_metric_tsp`;
- direct/executable KPI separation and experiment UIs.

The upstream SCoPP license and copyright information are available in its official repository.

## Runtime dependencies

The project installs and imports the following third-party Python packages rather than vendoring their source code:

- PyYAML
- Matplotlib
- NumPy
- scikit-learn
- Shapely

The test environment additionally uses pytest. Each dependency is distributed under the terms provided by its maintainers.

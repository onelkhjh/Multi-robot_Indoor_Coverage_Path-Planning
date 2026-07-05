# Official SCoPP parity audit

## Sources

- Collins et al., *Scalable Coverage Path Planning of Multi-Robot Teams for
  Monitoring Non-Convex Areas*, arXiv:2103.14709.
- `adamslab-ub/SCoPP` public repository, `main` branch:
  `monitoring_algorithms.py` and `SCoPP_settings.py`, retrieved 2026-07-05.

This audit separates the published/official behavior from the indoor research
adaptations in this repository.

## Confirmed official behavior

| Stage | Official implementation |
|---|---|
| Cell width | Computes `W = 2 h tan(F/2)`, casts to `int`, then reduces an odd width by one. |
| Cell acceptance | Samples the cell perimeter every 3 m and accepts only a complete expected perimeter inside the AOI polygon. |
| Partitioning | Uses `MiniBatchKMeans`, `n_clusters=node_count`, tolerance `cell_size/8`, maximum 10 iterations. |
| Cluster/node association | Greedily associates each cluster with a remaining robot start using the nearest cluster cell. |
| Conflict detection | A cell is conflicting when its sampled boundary contains more than one cluster label. |
| Conflict bid | Fixes `distance_bias = round(d0 / cell_size) * B` before auction; default `B=0.5`. It then minimizes `current_cell_count + distance_bias`. |
| Tie behavior | Comparison uses strict `<`; the first candidate remains winner on equal cost. |
| Default CPP | Repeated Euclidean nearest neighbor over cell centres. The public `nn` branch requests brute-force neighbors despite other branches using KD-tree. |
| Route closure | Adds the robot start at the beginning and end of every path. |

## Corrections applied

- Conflict distance bias is now calculated once, normalized in cell widths,
  rounded, and multiplied by `B`.
- Conflict bids now reuse that fixed bias while the assigned cell count changes.
- Coverage path distance and visualization now include return to the node start.
- Exact ties remain resolved by stable candidate order.

## Deliberate indoor adaptations

- Input coordinates are local Cartesian metres; geographic conversion is out of
  scope.
- Floating-point cell width is retained. Official integer/even rounding would
  reduce the current `0.924 m` indoor footprint to zero and is not usable at
  laboratory scale.
- `any_overlap` is available to cover the complete AOI. Official code behaves
  more like a fully-contained perimeter policy.
- Perimeter spacing defaults to `W/8`; official code fixes it at 3 m, which is
  larger than the entire indoor cell.
- The local nearest-neighbor implementation uses a KD-tree as described by the
  paper; the official default code currently selects brute force.

These adaptations must be reported in indoor experiment results and must not be
presented as byte-for-byte official-code reproduction.

## Remaining blocking difference

The current clustering implementation is deterministic full-batch Lloyd
clustering initialized at node starts. Official code uses stochastic
`MiniBatchKMeans` and associates clusters to robot starts afterward. Therefore
the current partition is a paper-guided deterministic implementation, not exact
official-code parity.

Before publishing direct numeric comparisons with the official repository:

1. add an `official_minibatch` profile using a pinned scikit-learn version and
   recorded random seed;
2. implement the official greedy cluster-to-node association;
3. preserve the current deterministic profile as an explicit research variant;
4. compare cell labels, conflicts, auction winners and final paths on a shared
   Cartesian fixture.

# Map schema v1

The implementation accepts UTF-8 YAML or JSON. Indoor laboratory coordinates
use local Cartesian `[x, y]` metres. The map's physical origin and positive axis
directions must be recorded with the experiment. Geographic coordinates are out
of scope.

The default `paper_center` policy follows the paper's cell-centre observation
model: a cell is selected when its centre is in the AOI. The research extension
`any_overlap` includes every cell with positive-area AOI overlap. Both policies
reject cells with positive-area overlap with a no-fly zone.

`nodes` is the general project term. In a paper reproduction, every node is a
robot/UAV. See `examples/maps` for complete files.

The official paper does not define this serialization format or the precise
boundary-cell rule. Results must therefore record the selected policy.

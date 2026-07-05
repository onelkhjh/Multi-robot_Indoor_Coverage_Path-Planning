# SCoPP 알고리즘 연결 인터페이스 계획

## 1. 목적과 범위

이 문서는 맵 계층의 출력을 이후 SCoPP 단계인 Lloyd 계열 clustering, conflict-cell greedy auction, KD-tree nearest-neighbor coverage route에 전달하는 계약을 정의한다. 현재 단계에서는 구현 코드를 변경하지 않는다.

맵 계층은 geometry와 결정적 pseudo-discretization을 소유하고, 알고리즘 계층은 그 결과를 읽기만 한다. 알고리즘 계층이 polygon을 다시 격자화하거나 cell ID를 재발급해서는 안 된다.

## 2. 공통 입력 계약

알고리즘의 단일 진입 입력은 투영 완료된 맵과 격자화 결과의 묶음이어야 한다.

```python
@dataclass(frozen=True, slots=True)
class AlgorithmMap:
    projected_map: ProjectedMap
    discretized_map: DiscretizedMap

    # 다음 값은 위 두 객체로부터 검증 후 만든 결정적 view다.
    cell_ids: tuple[str, ...]
    cell_centers_xy_m: NDArray[Shape["n_cells, 2"], Float64]
    perimeter_points_xy_m: NDArray[Shape["n_points, 2"], Float64]
    perimeter_cell_index: NDArray[Shape["n_points"], Int64]
    robot_ids: tuple[str, ...]
    robot_starts_xy_m: NDArray[Shape["n_robots, 2"], Float64]
```

필수 불변조건은 다음과 같다.

- 모든 계산 좌표는 `(x, y)` 순서의 Cartesian metre이다. 위경도 입력을 알고리즘에 직접 전달하지 않는다.
- `cell_ids[i]`, `cell_centers_xy_m[i]`, `CoverageCell`의 순서는 동일하며 `(row, col)` 결정적 순서를 보존한다.
- `perimeter_cell_index[j]`는 perimeter point `j`를 생성한 cell index이다. 좌표만으로 소유 cell을 역추론하지 않는다.
- perimeter point 순서는 cell 순서, 이어서 각 cell의 반시계 표본 순서이다.
- robot index는 입력 `robot_starts` 순서를 따르되 결과마다 `robot_ids`를 함께 보존한다.
- 배열은 유한한 `float64`이고 외부에서 변경할 수 없는 view 또는 복사본으로 제공한다.
- `DiscretizedMap.source`와 `ProjectedMap`이 동일한 투영 맵/설정에서 생성됐는지 fingerprint 또는 명시적 identity로 검증한다.
- 빈 cell, 빈 robot, 중복 cell ID 및 중복 robot ID는 알고리즘 진입 전에 명시적 예외로 거부한다.

`RejectedCell`은 진단과 시각화에만 쓰며 clustering, auction, route 입력에 포함하지 않는다. `coverage_ratio`는 실험 분석에는 보존하지만 논문 근거가 확인되기 전까지 clustering weight로 사용하지 않는다.

## 3. Lloyd 계열 clustering 연결

### 입력

```python
@dataclass(frozen=True, slots=True)
class ClusteringInput:
    robot_ids: tuple[str, ...]
    initial_generators_xy_m: NDArray[Shape["n_robots, 2"], Float64]
    sample_points_xy_m: NDArray[Shape["n_points, 2"], Float64]
    sample_cell_index: NDArray[Shape["n_points"], Int64]
    convergence_tolerance_m: float
    max_iterations: int
    seed: int | None
```

`sample_points_xy_m`에는 각 유효 cell의 perimeter samples를 전달한다. 초기 generator는 robot 시작점이다. Lloyd 반복 결과는 점 단위 cluster label을 반환해야 하며, 이후 conflict 검출을 위해 cell 소유 관계를 잃지 않아야 한다.

```python
@dataclass(frozen=True, slots=True)
class ClusteringResult:
    generator_xy_m: NDArray[Shape["n_robots, 2"], Float64]
    sample_labels: NDArray[Shape["n_points"], Int64]
    iterations: int
    converged: bool
```

검증 조건:

- label은 `[0, n_robots)`이고 모든 sample에 정확히 하나가 존재한다.
- 동일 입력, seed, 동점 정책에서 결과가 결정적이다.
- 빈 cluster가 생겼을 때 generator 유지/재초기화/실패 중 어느 정책인지 명시한다.
- 종료 조건은 좌표 이동량의 norm과 단위를 명시한다.

## 4. conflict-cell 검출과 auction 연결

하나의 cell에서 나온 perimeter samples가 둘 이상의 cluster label을 가지면 conflict cell 후보가 된다. 단일 cluster만 나타나는 cell은 해당 robot에 직접 할당한다.

```python
@dataclass(frozen=True, slots=True)
class CellPartition:
    uncontested_by_robot: tuple[tuple[int, ...], ...]
    conflict_cell_indices: tuple[int, ...]
    candidate_robots_by_cell: tuple[tuple[int, ...], ...]

@dataclass(frozen=True, slots=True)
class AuctionInput:
    cell_ids: tuple[str, ...]
    cell_centers_xy_m: NDArray[Shape["n_cells, 2"], Float64]
    robot_starts_xy_m: NDArray[Shape["n_robots, 2"], Float64]
    clustering: ClusteringResult
    partition: CellPartition
    distance_bias: float
```

auction 결과는 각 cell에 정확히 하나의 robot index를 부여하는 `owner_by_cell` 배열로 반환한다. cell ID 순서를 유지해 clustering과 route 단계 사이에서 set 순서에 의존하지 않게 한다.

거리 계산은 최소한 다음 항목을 분리해서 기록해야 한다.

- conflict cell 중심과 현재 cluster 중심(generator) 사이 거리
- conflict cell 중심과 robot 초기 위치 사이 거리
- 논문의 bias `B`가 어느 거리 항에 어떻게 적용되는지
- 동일 bid의 결정적 동점 처리(권고: robot index, 그 다음 cell index)

auction 완료 후 각 cell은 정확히 하나의 owner를 가져야 하며, candidate가 없는 conflict cell이나 범위 밖 owner는 실패로 처리한다.

## 5. KD-tree nearest-neighbor route 연결

```python
@dataclass(frozen=True, slots=True)
class RouteInput:
    robot_id: str
    start_xy_m: XY
    owned_cell_indices: tuple[int, ...]
    cell_centers_xy_m: NDArray[Shape["n_cells, 2"], Float64]

@dataclass(frozen=True, slots=True)
class CoverageRoute:
    robot_id: str
    ordered_cell_indices: tuple[int, ...]
    waypoints_xy_m: tuple[XY, ...]
    path_length_m: float
```

KD-tree에는 해당 robot 소유 cell의 중심만 넣는다. 첫 query 기준점은 robot 시작 위치이고, 방문한 점을 제거하거나 비활성화한 뒤 직전 방문 중심에서 반복한다. 결과의 waypoint는 `ordered_cell_indices`로부터 재구성 가능해야 하며 각 소유 cell을 정확히 한 번 포함해야 한다.

동일 거리 후보는 전역 cell index 또는 cell ID 순서로 결정한다. robot이 소유한 cell이 없으면 빈 route를 정상 결과로 반환할지 실패시킬지 정책을 고정해야 한다. 서로 분리된 effective-area component 사이를 잇는 직선이 no-fly zone/AOI 밖을 통과할 수 있으므로 이 route는 우선 **방문 순서**이지 충돌 없는 실제 비행 궤적이라고 간주하면 안 된다.

## 6. 모듈 경계 권고

```text
src/scopp/
  map/                  # 현재 계획: 입력, 투영, geometry, grid
  algorithm/
    adapters.py         # ProjectedMap + DiscretizedMap -> AlgorithmMap
    clustering.py       # Lloyd 계열 반복
    conflicts.py        # sample label -> cell partition
    auction.py          # conflict cell 소유권 결정
    routing.py          # KD-tree nearest-neighbor 방문 순서
    models.py           # 위 알고리즘 입력/결과 불변 타입
```

`map`은 `algorithm`을 import하지 않는다. `algorithm.adapters`만 맵 공개 타입을 알고, 나머지 알고리즘 모듈은 수치 배열과 stable index 계약에 의존한다. Shapely와 projection 객체는 알고리즘 핵심 함수에 전달하지 않는다.

## 7. 논문 근거가 아직 불확실한 항목

다음은 현재 문서만으로 “논문 그대로”라고 확정할 수 없다.

1. Lloyd 입력이 cell 전체 perimeter 표본인지, 유효 영역과 교차한 경계 표본인지와 정확한 표본 간격.
2. Lloyd centroid를 perimeter point의 산술평균으로 계산하는지, cell/면적 가중치를 사용하는지.
3. 수렴 허용오차 `W/8`, 최대 10회가 모든 실험의 고정값인지 및 이동량 norm 정의.
4. 초기 generator가 항상 robot 초기 위치인지, robot 수와 시작점 수가 다를 때의 매핑.
5. 빈 cluster 처리와 거리 동점 처리.
6. conflict cell 정의가 “한 cell perimeter에 복수 label”과 정확히 일치하는지.
7. greedy auction의 bid 식, `d_B(r) = d_0(r) * B` 적용 위치, `B = 0.5`의 의미와 갱신 순서.
8. auction candidate가 perimeter label에 나타난 robot으로 제한되는지 모든 robot인지.
9. nearest-neighbor 경로가 cell 중심만 방문하는지, 시작점을 결과 waypoint에 포함하는지, 동일 거리 동점 규칙.
10. KD-tree를 매 단계 재구축하는지 lazy deletion을 쓰는지. 이는 결과보다 성능 문제지만 재현 시간에 영향을 준다.
11. 불연속 AOI/no-fly zone 사이 transit의 안전 경로를 논문 알고리즘이 보장하는지.
12. `18 x 14 degree` 카메라에서 정사각 cell 폭과 perimeter를 정할 때 어느 FoV 성분을 쓰는지.

이 항목은 `paper-verifier`가 논문 section/equation/algorithm 또는 저자 공식 코드 위치를 제공한 뒤 기본값으로 확정한다. 확인 전에는 설정과 결과 metadata에 선택값을 노출하고 프로젝트 가정으로 표시한다.

## 8. 구현 전 인수 기준

- 고정 맵에서 adapter가 cell/sample/robot 배열과 역매핑을 byte-for-byte 동일하게 만든다.
- 모든 알고리즘 결과가 cell ID와 robot ID로 추적 가능하다.
- clustering label에서 conflict cell과 uncontested cell을 손계산 fixture대로 복원한다.
- auction 후 모든 유효 cell의 owner가 정확히 하나이다.
- route가 각 owner의 cell을 정확히 한 번 방문하고 다른 robot cell을 포함하지 않는다.
- x/y, row/col, lon/lat 순서가 공개 타입과 테스트 이름에 명시된다.
- 논문 미확정 정책은 숨은 상수로 구현하지 않고 설정 및 metadata로 노출된다.

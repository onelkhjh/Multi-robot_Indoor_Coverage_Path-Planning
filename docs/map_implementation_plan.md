# SCoPP 논문형 맵 구현 계획

## 1. 범위와 완료 조건

이 문서는 SCoPP 전체 알고리즘보다 먼저 구현할 맵 계층의 실행 계획이다. 첫 마일스톤은 하나의 맵 정의 파일에서 다음 결과를 결정적으로 생성하는 것이다.

- 비볼록 AOI와 0개 이상의 no-fly zone을 로드하고 검증한다.
- 실험실 로컬 Cartesian `(x, y)` 미터 좌표를 입력으로 사용한다.
- 고도와 카메라 FoV로 정사각형 coverage cell 크기를 계산한다.
- AOI에 포함되고 no-fly zone과 충돌하지 않는 cell을 생성한다.
- cell 중심점과 perimeter 표본점을 생성한다.
- AOI, hole/no-fly zone, 포함/제외 cell, 로봇 시작점을 상태 변경 없이 렌더링한다.
- 동일 입력과 설정에서 cell ID, 좌표, 표본점 순서 및 그림이 재현된다.

이 단계에는 clustering, auction, route planning, ROS 2/Crazyswarm2 연동을 넣지 않는다.

## 2. 제안 패키지 구조

```text
pyproject.toml
src/
  scopp/
    __init__.py
    map/
      __init__.py
      models.py          # 불변 도메인 모델과 enum
      schema.py          # YAML/JSON 파싱 및 구조 검증
      footprint.py       # FoV 기반 cell 크기 계산
      geometry.py        # polygon 정규화와 공간 predicate
      grid.py            # pseudo-discretization과 perimeter 표본
      io.py              # 공개 load/dump 진입점
      visualization.py   # matplotlib 렌더러
examples/
  maps/
    composite.yaml       # 비볼록 AOI + hole/no-fly zone
    paper_like.yaml      # 논문 그림을 본뜬 근사 예제(실측값 아님)
scripts/
  render_map.py          # YAML -> PNG/SVG + 선택적 cell CSV
tests/
  map/
    test_schema.py
    test_coordinates.py
    test_footprint.py
    test_geometry.py
    test_grid.py
    test_visualization.py
docs/
  map_schema.md
  map_implementation_plan.md
```

Python 3.11 이상을 기준으로 한다. 현재 구현 의존성은 `PyYAML`, `matplotlib`, 테스트는 `pytest`로 제한한다. 패키지는 `src` layout을 사용하며 맵 모듈에서 알고리즘 모듈을 import하지 않는다.

## 3. 데이터 모델

`models.py`의 공개 타입은 `@dataclass(frozen=True, slots=True)`로 정의한다. 좌표 배열을 외부에 직접 노출하지 않고 tuple로 정규화해 입력 이후 변경을 막는다.

```python
type XY = tuple[float, float]
type LonLat = tuple[float, float]  # 항상 longitude, latitude 순서

class CoordinateKind(str, Enum):
    CARTESIAN = "cartesian"
    GEOGRAPHIC = "geographic"

class CellBoundaryPolicy(str, Enum):
    ANY_OVERLAP = "any_overlap"
    FULLY_CONTAINED = "fully_contained"
    CENTER_INSIDE = "center_inside"
    MIN_COVERAGE = "min_coverage"

@dataclass(frozen=True, slots=True)
class CoordinateReference:
    kind: CoordinateKind
    unit: Literal["m", "deg"]
    origin: LonLat | None = None
    projected_crs: str | None = None

@dataclass(frozen=True, slots=True)
class PolygonSpec:
    exterior: tuple[XY, ...]
    holes: tuple[tuple[XY, ...], ...] = ()

@dataclass(frozen=True, slots=True)
class RobotStart:
    id: str
    position: XY

@dataclass(frozen=True, slots=True)
class SensorSpec:
    altitude_m: float
    fov_deg: float

@dataclass(frozen=True, slots=True)
class GridSpec:
    origin: XY | None
    boundary_policy: CellBoundaryPolicy
    minimum_coverage: float | None
    perimeter_spacing_m: float | None

@dataclass(frozen=True, slots=True)
class MapDefinition:
    schema_version: str
    name: str
    coordinates: CoordinateReference
    aoi: PolygonSpec
    no_fly_zones: tuple[PolygonSpec, ...]
    robot_starts: tuple[RobotStart, ...]
    sensor: SensorSpec
    grid: GridSpec

@dataclass(frozen=True, slots=True)
class CoverageCell:
    id: str                 # "r{row}_c{col}", 음수는 m 접두어 사용
    row: int
    col: int
    center: XY
    vertices: tuple[XY, XY, XY, XY]
    coverage_ratio: float
    perimeter_samples: tuple[XY, ...]

@dataclass(frozen=True, slots=True)
class RejectedCell:
    row: int
    col: int
    center: XY
    reason: Literal["outside_aoi", "crosses_aoi", "intersects_no_fly_zone",
                    "below_minimum_coverage"]

@dataclass(frozen=True, slots=True)
class DiscretizedMap:
    source: MapDefinition
    cell_width_m: float
    effective_area: PolygonSpec | tuple[PolygonSpec, ...]
    cells: tuple[CoverageCell, ...]
    rejected_cells: tuple[RejectedCell, ...]
```

불변조건은 다음과 같다.

- Cartesian 좌표와 모든 길이는 미터, geographic 원본은 경도/위도 degree이다.
- polygon ring은 파일에서 닫혀 있어도 로더가 마지막 중복점을 제거한다. 내부 모델은 닫는 점을 중복 저장하지 않는다.
- exterior와 hole의 방향은 로더가 Shapely `orient(..., sign=1.0)` 기준으로 정규화한다.
- 최소 3개의 서로 다른 꼭짓점, 유한한 수, 양의 면적, valid geometry를 요구한다.
- no-fly zone은 AOI 밖에 일부 존재할 수 있으나 실제 금지 영역은 AOI와의 교집합만 사용한다.
- robot ID는 유일하며 시작점은 기본적으로 `AOI - no_fly_zones` 안 또는 경계에 있어야 한다.
- `0 < fov_deg < 180`, `altitude_m > 0`, `0 <= minimum_coverage <= 1`이다.

## 4. YAML 스키마 v1

첫 버전은 아래 형태를 고정한다. JSON도 동일한 object 구조를 사용한다.

```yaml
schema_version: "1.0"
name: composite-example

coordinates:
  kind: cartesian       # cartesian | geographic
  unit: m               # cartesian=m, geographic=deg
  # geographic일 때 필수:
  # origin: [127.0000, 37.5000]   # [longitude, latitude]
  # projected_crs: auto_utm       # auto_utm 또는 EPSG 문자열

aoi:
  exterior:
    - [0.0, 0.0]
    - [120.0, 0.0]
    - [120.0, 40.0]
    - [70.0, 40.0]
    - [70.0, 100.0]
    - [0.0, 100.0]
  holes:
    - [[15.0, 55.0], [35.0, 55.0], [35.0, 75.0], [15.0, 75.0]]

no_fly_zones:
  - exterior: [[80.0, 10.0], [105.0, 10.0], [105.0, 30.0], [80.0, 30.0]]
    holes: []

robot_starts:
  - id: robot-01
    position: [5.0, 5.0]
  - id: robot-02
    position: [5.0, 15.0]

sensor:
  altitude_m: 20.0
  fov_deg: 60.0

grid:
  origin: [0.0, 0.0]             # 생략 시 effective area bbox의 (minx, miny)
  boundary_policy: any_overlap
  minimum_coverage: null          # min_coverage 정책에서만 필수
  perimeter_spacing_m: null       # null이면 W/8
```

검증 오류는 JSON Pointer에 준하는 경로를 포함한 `MapValidationError(path, message)`로 반환한다. 알 수 없는 키는 오타를 숨기지 않도록 거부한다. YAML implicit boolean/date 변환의 영향을 막기 위해 enum과 version은 문자열만 허용한다.

`geographic` 입력에서는 모든 polygon과 시작점 좌표를 먼저 지정 projection으로 변환한 뒤 `MapDefinition`의 계산용 복제본을 만든다. 원본 geographic 정의와 투영 메타데이터를 보존해 그림 축이나 export에서 역변환할 수 있게 한다. 자동 UTM은 origin의 zone으로 고정하며 antimeridian 통과 또는 여러 UTM zone에 걸친 AOI는 v1에서 명시적으로 거부한다.

## 5. 공개 API

### 로딩과 좌표 변환

```python
def load_map(path: str | Path) -> MapDefinition: ...
def parse_map(data: Mapping[str, object]) -> MapDefinition: ...
def project_map(definition: MapDefinition) -> ProjectedMap: ...
def make_transformer(reference: CoordinateReference) -> CoordinateTransformer: ...
```

`ProjectedMap`은 계산에 사용할 미터 좌표의 `MapDefinition`, 원래 CRS, 대상 CRS, 순/역 transformer를 가진다. `pyproj.Transformer(..., always_xy=True)`를 강제해 경도/위도와 x/y 순서 혼동을 차단한다.

### footprint

```python
def coverage_width(altitude_m: float, fov_deg: float) -> float:
    """W = 2 * h * tan(radians(F) / 2)."""
```

FoV는 degree 입력, 결과는 meter이다. 계산이 유한하지 않거나 0 이하이면 `ValueError`이다.

### geometry와 격자화

```python
def build_effective_geometry(map_: ProjectedMap) -> BaseGeometry: ...

def discretize_map(
    map_: ProjectedMap,
    *,
    include_rejected: bool = False,
) -> DiscretizedMap: ...

def sample_cell_perimeter(
    vertices: Sequence[XY],
    spacing_m: float,
) -> tuple[XY, ...]: ...
```

격자 생성 절차는 다음처럼 고정한다.

1. `W`를 계산하고 `effective = make_valid(AOI) - union(no_fly_zones)`를 만든다.
2. 명시한 grid origin, 아니면 AOI bbox의 `(minx, miny)`를 anchor로 사용한다.
3. bbox를 덮는 정수 `(row, col)` 범위를 floor/ceil로 계산한다.
4. cell은 `[x0, x0+W] x [y0, y0+W]`, 중심은 정확한 산술값으로 만든다.
5. row 우선, 그 안에서 col 오름차순으로 판정해 결정적 순서를 만든다.
6. 정책에 따라 채택한다.
   - `any_overlap`(기본): `cell.intersection(AOI).area > 0`이고 no-fly zone과 양의 면적 교집합이 없으면 포함한다. 실제 AOI 교집합은 `coverage_geometry`에 저장한다.
   - `fully_contained`: `effective.covers(cell_polygon)`인 cell만 포함한다.
   - `center_inside`: `effective.covers(center)`이고 cell 면적이 no-fly zone과 0보다 큰 교집합을 갖지 않을 때 포함한다.
   - `min_coverage`: `cell.intersection(effective).area / cell.area >= threshold`이고 no-fly zone과 면적 교집합이 없을 때 포함한다.
7. `coverage_ratio`는 모든 정책에서 동일 식으로 기록한다.
8. perimeter 표본은 좌하단 꼭짓점에서 시작해 반시계 방향으로 진행한다. 각 변에서 시작점은 포함하고 끝점은 다음 변이 소유하여 중복하지 않는다. 간격은 `edge_length / ceil(edge_length / requested_spacing)`으로 균등화한다.

경계 접촉은 면적 침범과 구별한다. no-fly zone 경계에 선/점으로 접하는 cell은 허용하는 것을 v1 기본안으로 두되, 논문 근거 확인 후 정책화할 수 있다. 부동소수 tolerance를 geometry 자체에 임의 buffer로 적용하지 않는다. 비교 tolerance가 필요하면 면적 비율 비교에만 `1e-12`를 사용하고 테스트로 고정한다.

Cell ID는 grid origin과 `(row, col)`에만 의존해야 하며 polygon 순서나 필터 결과에 따라 재번호화하지 않는다. 예: `r12_c4`, `rm1_c2`.

### 시각화

```python
@dataclass(frozen=True, slots=True)
class MapStyle:
    show_rejected: bool = False
    show_cell_ids: bool = False
    show_perimeter_samples: bool = False
    equal_aspect: bool = True

def plot_map(
    map_: ProjectedMap,
    discretized: DiscretizedMap | None = None,
    *,
    ax: matplotlib.axes.Axes | None = None,
    style: MapStyle = MapStyle(),
) -> tuple[Figure, Axes]: ...

def save_map_figure(
    path: str | Path,
    map_: ProjectedMap,
    discretized: DiscretizedMap | None = None,
    *,
    style: MapStyle = MapStyle(),
    dpi: int = 160,
) -> None: ...
```

렌더러는 입력 모델을 변경하지 않고 `Figure, Axes`를 반환한다. AOI 외곽은 검정 실선, hole/no-fly zone은 hatch, 포함 cell은 반투명 파랑, 제외 cell은 선택적으로 회색/빨강, 시작점은 robot ID가 붙은 서로 다른 marker로 표시한다. Cartesian 축은 `x (m)`, `y (m)`로 표시하며 항상 equal aspect를 적용한다. 테스트 환경에서는 `Agg` backend를 사용한다.

CLI 예시는 다음과 같다.

```powershell
python scripts/render_map.py examples/maps/composite.yaml --output artifacts/composite.png --show-rejected
```

## 6. 예외와 실패 정책

- 파싱 실패: `MapParseError`에 파일 위치와 하위 parser 오류를 보존한다.
- 스키마 실패: `MapValidationError`로 잘못된 field 경로를 명시한다.
- self-intersection, zero-area polygon은 자동 수정하지 않고 거부한다. `make_valid`는 이미 검증된 geometry 간 difference 결과 정규화에만 사용한다.
- effective area가 비면 `EmptyCoverageAreaError`이다.
- 시작점이 금지/외부 영역이면 해당 robot ID와 좌표를 포함해 거부한다.
- `MultiPolygon` effective area는 정상 입력이며 모든 component를 동일 grid에서 처리한다.
- 빈 cell 집합은 geometry가 유효하더라도 `NoCoverageCellsError`로 명확히 실패시킨다. 호출자가 정책이나 고도를 조정해야 한다.

## 7. 테스트 및 구현 순서

1. `models.py`, `schema.py`, `io.py`: 최소 YAML과 unknown key, 잘못된 ring, 중복 robot, 단위 불일치 테스트.
2. `coordinates.py`: 알려진 UTM 기준점 round-trip, `always_xy`, Cartesian identity 테스트.
3. `footprint.py`: `h=20`, `F=60`에서 `W≈23.09401077 m`, 각도/고도 실패 테스트.
4. `geometry.py`: concave AOI, hole, 겹치는 no-fly zone, disconnected result 테스트.
5. `grid.py`: 직사각형의 정확한 cell 수, concavity 제외, hole 제외, 경계 접촉, origin 이동, 결정적 ID/순서, perimeter 중복 없음 테스트.
6. `visualization.py`: artist 종류/개수, axis label/aspect, headless PNG 생성 테스트. 픽셀 단위 golden test는 matplotlib 버전 변화에 취약하므로 쓰지 않는다.
7. 두 예제 파일과 CLI를 추가하고 README 실행 예시를 연결한다.

필수 검증 명령은 다음과 같다.

```powershell
python -m pytest
python -m compileall src tests scripts
python scripts/render_map.py examples/maps/composite.yaml --output artifacts/composite.png --show-rejected
```

## 8. 논문 검증 전 가정과 결정 보류 항목

아래는 `paper-verifier`의 근거가 아직 없으므로 논문 사실로 간주하지 않는다.

| 항목 | 현재 설계 가정 | 검증 후 영향 |
|---|---|---|
| cell 채택 규칙 | 기본 `any_overlap`; AOI 양의 면적 교차는 포함, no-fly 양의 면적 교차는 제외 | 사용자 확정 연구 정책. 논문 규칙과 다르면 재현 보고서에 차이 명시 |
| grid anchor/orientation | bbox 최소점, world x/y 정렬 | 논문이 별도 origin/회전을 쓰면 `GridSpec.rotation_deg` 추가 |
| perimeter 간격 | AGENTS 지침의 `W/8` | 논문 수식/알고리즘과 대조 후 기본값 확정 |
| perimeter 표본 위치 | cell 전체 둘레 | 논문이 AOI와 겹친 경계만 쓰면 표본 API를 geometry intersection 기반으로 변경 |
| no-fly 경계 접촉 | 면적 침범이 아니면 허용 | 안전 여유 또는 strict exclusion 근거가 있으면 policy 추가 |
| holes와 no-fly zone 관계 | 모두 coverage 제외, 시각 의미만 구분 | 논문 정의에 따라 하나의 obstacle 모델로 통합 가능 |
| geographic projection | origin 기반 단일 UTM | 논문이 별도 local tangent-plane 변환을 명시하면 transformer 교체 |
| FoV | 단일 full-angle, 정사각 footprint | 수평/수직 FoV 구분 시 직사각 cell 또는 보수적 최소 폭 정책 필요 |
| 논문형 예제 좌표 | 그림을 시각적으로 근사한 synthetic data | 원본 실험 좌표 확보 시 별도 재현 데이터셋으로 교체 |

가정은 schema default로 조용히 숨기지 않는다. 예제 파일에 선택된 정책을 명시하고, 실행 결과 metadata에도 정책과 projection을 기록한다. `paper-verifier`가 근거를 전달하면 이 표를 `docs/paper_spec.md`의 traceability 항목과 연결한 뒤 기본값을 확정한다.

## 9. 첫 구현 PR의 인수 기준

- `composite.yaml`에서 비볼록 AOI, 내부 hole, 별도 no-fly zone, 2개 시작점이 한 그림에 구분되어 보인다.
- `paper_like.yaml`은 파일 상단 주석과 문서에서 synthetic approximation임을 명시한다.
- 모든 cell이 선택된 boundary policy를 만족하며 no-fly zone과 양의 면적 교집합이 없다.
- 같은 명령을 두 번 실행했을 때 cell ID와 좌표 export가 byte-for-byte 동일하다.
- 좌표, 길이, FoV 단위와 polygon 경계 규칙이 공개 API docstring 및 `docs/map_schema.md`에 기재된다.
- 맵 패키지는 clustering/auction/route 또는 하드웨어 의존성을 갖지 않는다.
- 전체 테스트와 compile 검증이 통과하고, 해석 가정은 위 표에서 누락 없이 추적된다.

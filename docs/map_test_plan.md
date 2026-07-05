# SCoPP 논문형 맵 독립 검증 계획

## 1. 목적과 범위

이 문서는 SCoPP 첫 번째 마일스톤인 맵 데이터 모델, 좌표 변환,
pseudo-discretization, 유효 cell 판정 및 2D 시각화를 구현 코드와 독립적으로
검증하기 위한 계획이다. clustering, auction, coverage route는 범위 밖이다.

테스트의 기대값은 가능하면 손으로 계산한 값 또는 별도의 단순 기하 계산으로
만든다. 제품 코드의 내부 helper를 기대값 생성에 재사용하지 않는다. 모든 테스트는
고정된 입력 파일, 좌표계, 단위, 경계 포함 정책을 기록해야 한다.

## 2. 공통 합격 조건

- 입력 좌표 순서는 `(x, y)`, 격자 인덱스는 `(row, col)`로 구분된다.
- 거리와 고도 단위는 metre, FoV 입력 단위는 명시적으로 degree 또는 radian이다.
- 같은 입력과 설정은 실행 순서 및 반복 실행에 무관하게 같은 cell 집합과 순서를 낸다.
- AOI와 양의 면적으로 겹치는 cell은 유효 후보이며, 점·선 접촉만 하는 cell은 제외한다.
- no-fly zone과 양의 면적으로 겹치는 cell은 비행 가능 cell이 될 수 없다.
- 경계 접촉 cell의 포함 정책은 스키마/API 문서에 하나로 정의되고 모든 경로에서 동일하다.
- 부동소수점 비교 기본 허용오차는 절대 `1e-9`, 지리 좌표 왕복은 지상거리 `0.01 m`이다.
  외부 라이브러리 정밀도가 이를 만족하지 못하면 측정 근거와 함께 완화한다.
- 잘못된 polygon, 단위, FoV, 고도에는 묵시적 보정 대신 구체적인 예외가 발생한다.

## 3. 고정 fixture

1. `convex_10m`: `(0,0)-(10,0)-(10,10)-(0,10)` 정사각 AOI.
2. `concave_l`: `[(0,0),(10,0),(10,4),(4,4),(4,10),(0,10)]` L자 AOI.
3. `hole_center`: 20 m 정사각 AOI와 `(8,8)-(12,8)-(12,12)-(8,12)` no-fly zone.
4. `disconnected`: 서로 떨어진 두 개의 4 m 정사각 AOI component.
5. `boundary_cases`: polygon 꼭짓점, 변 위, 변에서 `epsilon` 안/밖의 점.
6. `paper_like`: 비볼록 외곽선, 복수 no-fly zone, 불연속 component 및 로봇 시작점을
   포함하는 고정 JSON/YAML. 논문 그림의 정확한 좌표를 알 수 없다면 이름과 메타데이터에
   `visual_approximation: true`를 기록한다.

각 fixture는 vertex 순서를 반대로 한 변형과 시작 vertex를 순환 이동한 변형도 가진다.

## 4. 단위 테스트

### 4.1 스키마와 로더

- 최소 유효 JSON과 YAML을 각각 로드해 정규화 결과가 동일한지 확인한다.
- 누락 필드, NaN/Infinity, 중복만 있는 ring, 3개 미만의 고유 꼭짓점,
  self-intersection, AOI 밖 hole, 겹치는 hole, 음수 고도, `F <= 0`, `F >= 180°`,
  알 수 없는 단위를 각각 거부한다.
- 닫힘 꼭짓점을 명시한 ring과 생략한 ring이 동일하게 처리되는지 확인한다.
- 합격: 정상 입력은 손실 없이 로드되고 실패 입력은 필드 경로를 포함한 예외를 낸다.

### 4.2 점과 polygon 판정

- convex/concave AOI의 명백한 내부와 외부 점을 판정한다.
- 외곽 변, 외곽 꼭짓점, hole 변, hole 꼭짓점을 각각 검사한다.
- no-fly zone 내부 점은 AOI 내부여도 비행 가능하지 않아야 한다.
- 두 component 사이 점은 비행 가능하지 않아야 한다.
- 합격: 손계산 truth table과 100% 일치하고, 문서화된 경계 정책이 외곽선과 hole에
  모순 없이 적용된다. `epsilon`은 좌표 스케일에 따라 임의로 결과를 뒤집지 않는다.

### 4.3 FoV 기반 cell 폭

독립 기대식은 `W = 2 h tan(F/2)`이다.

| h (m) | F | 기대 W (m) |
|---:|---:|---:|
| 10 | 90° | 20 |
| 10 | 60° | 11.5470053837925 |
| 25 | 45° | 20.7106781186548 |

- degree/radian 입력을 따로 검사하며 명시적 변환 후 같은 결과인지 확인한다.
- `h` 두 배일 때 `W`도 두 배인 metamorphic test를 수행한다.
- 합격: 표의 값과 상대오차 `1e-12` 이내이며 유효 입력에서 양의 유한값이다.

### 4.4 cell 기하

- 알려진 origin과 `W`로 첫 cell 및 임의 `(row,col)` cell의 중심과 네 꼭짓점을 검사한다.
- 중심 간 x/y 간격이 각각 정확히 `W`인지, 면적이 `W^2`인지 확인한다.
- 중심에서 네 변까지 거리가 `W/2`이고 perimeter 표본이 실제 경계 위인지 확인한다.
- 합격: 허용오차 안에서 기대 좌표와 일치하며 row/col과 x/y 전치 오류가 없다.

### 4.5 유효 cell 판정

`convex_10m`에 정확히 나누어지는 `W=2`를 적용해 기준 cell 수를 손으로 산출한다.
이어서 AOI 경계 교차, concave notch 교차, hole 완전 포함, hole 경계 접촉, 아주 얇은
AOI 조각과 교차하는 cell을 검사한다.

- 기본 `any_overlap` 정책의 최소 불변조건: `intersection(cell, AOI).area > 0`이고
  `intersection(cell, no_fly).area == 0`이어야 한다. 경계 cell의 `coverage_geometry`는
  `intersection(cell, AOI)`와 기하적으로 같아야 한다.
- 다른 경계 정책을 채택한다면 그 정책별 기대 집합을 별도 fixture로 고정한다.
- 합격: 중심점 위치와 무관하게 AOI와 양의 면적으로 교차하는 cell을 포함하고, AOI에
  점·선으로만 접하는 cell과 no-fly zone과 양의 면적으로 겹치는 cell은 포함하지 않는다.
  cell 순서는 문서화된 정렬 순서를 따른다.

## 5. 속성 및 metamorphic 테스트

고정 seed로 유효 polygon과 hole을 생성해 다음 속성을 최소 500개 사례에서 검사한다.

- 모든 유효 cell의 폭/높이/면적은 각각 `W`, `W`, `W^2`이다.
- 유효 cell 내부의 대표점과 perimeter 표본은 비행 가능 영역 조건을 만족한다.
- 유효 cell끼리 내부 면적이 겹치지 않는다.
- polygon vertex 순서 반전 또는 시작 vertex 회전은 cell 집합을 바꾸지 않는다.
- 전체 geometry와 origin을 벡터 `v`만큼 평행 이동하면 모든 cell도 `v`만큼 이동한다.
- `W`가 동일하게 계산되는 `(h,F)` 조합은 동일한 cell 집합을 만든다.
- no-fly zone을 추가하면 유효 cell 수가 증가하지 않고, 제거하면 감소하지 않는다.
- AOI를 확대하면 고정 origin/grid에서 기존 유효 cell이 사라지지 않는다.
- 실패 시 seed와 최소화된 입력을 출력해 재현 가능해야 한다.

합격: 500개 전부 통과한다. 발견된 반례는 축소 후 회귀 fixture로 편입한다.

## 6. 회귀와 결정성

- 각 고정 fixture에 대해 정규화된 맵, cell ID, 중심, 꼭짓점, 유효/제외 사유를
  정렬한 canonical JSON snapshot을 보관한다.
- 동일 프로세스 10회, 새 프로세스 10회 실행 결과의 SHA-256이 같아야 한다.
- 가능한 CI 대상 OS/Python 버전 간에는 좌표를 정해진 정밀도로 반올림한 snapshot을 비교한다.
- 입력 polygon 순서, JSON key 순서, YAML 표현 차이는 결과를 바꾸지 않아야 한다.
- 합격: 의도적으로 승인한 변경 외 snapshot diff가 없고, diff에는 cell 추가/삭제와
  판정 사유가 사람이 읽을 수 있게 표시된다.

## 7. 실험실 좌표계 검증

- 모든 입력 좌표와 길이가 미터 단위인지 검증한다.
- 맵 메타데이터에 실험실 원점과 `+x`, `+y` 축의 물리적 방향을 기록한다.
- `coordinates.kind != cartesian` 또는 `unit != m` 입력을 명시적으로 거부한다.
- 알려진 실험실 기준점 사이의 좌표 거리를 실제 측정 거리와 비교한다.

## 8. 시각화 검증

### 8.1 구조 검증

- 렌더러 입력 전후 canonical map 객체가 동일한지 검사해 시각화가 상태를 바꾸지 않음을 보인다.
- AOI 외곽, 각 hole, 유효/제외 cell, 로봇 시작점이 서로 다른 artist/layer로 정확한 수만큼
  생성되는지 검사한다.
- axis aspect가 equal이고 축 단위, 범례, 제목이 존재하는지 확인한다.
- 시작점이 비행 불가 영역이면 렌더 전에 validation error가 발생해야 한다.

### 8.2 이미지 회귀

- 고정 backend, DPI, figure size, font, plotting-library 버전으로 PNG를 생성한다.
- 픽셀 완전 일치 대신 perceptual hash 거리와 구조 마스크 IoU를 사용한다.
- 합격: AOI/hole/cell 마스크 IoU 각각 `>= 0.995`, perceptual hash 거리는 승인한
  baseline 임계치 이하이며 주요 layer 누락은 hash와 무관하게 실패다.

### 8.3 논문 그림 근사치 검증

논문 그림은 데이터 원본이 아닌 시각적 기준이다. 그림에서 좌표를 추정해 만든 맵은 정확한
실험 데이터라고 주장하지 않는다. 검증은 다음의 구조적 특징으로 제한한다.

- 비볼록 AOI가 식별된다.
- no-fly zone 및 불연속 영역의 개수와 상대적 배치가 reference annotation과 일치한다.
- cell 크기가 전체 AOI scale에 비례해 육안으로 구분되고 cell이 금지영역을 침범하지 않는다.
- 로봇 시작점의 수와 대략적 상대 위치가 annotation과 일치한다.

reference 그림에 사람이 작성한 polygon/point annotation을 두고 렌더 결과와 비교한다.
합격 기준은 AOI/hole mask IoU `>= 0.90`, 시작점 매칭 거리 `<= AOI bounding-box diagonal의 2%`,
component와 hole 개수 100% 일치이다. 색상이나 글꼴 차이는 실패 사유가 아니다.

## 9. 오류 및 극단 사례

- 좌표 크기가 매우 크거나 매우 작을 때 tolerance가 안정적인지 검사한다.
- 폭이 `W`보다 작은 corridor, `W`와 정확히 같은 corridor, 거의 접하는 hole 두 개를 검사한다.
- robot start가 외곽/홀 경계, AOI 밖, NaN인 경우 정책에 맞게 거부되는지 검사한다.
- 유효 cell이 0개인 정상 geometry는 명확한 빈 결과를 내며 무한 반복하지 않아야 한다.
- 합격: crash, hang, 비결정적 결과가 없고 모든 거부에 입력 위치를 식별할 메시지가 있다.

## 10. 실행 및 승인 게이트

권장 pytest marker는 `unit`, `property`, `regression`, `visual`, `paper_approx`이다.

```powershell
python -m pytest -m "unit or property or regression"
python -m pytest -m visual
python -m pytest -m paper_approx
```

마일스톤 승인은 다음을 모두 만족해야 한다.

1. 단위/속성/회귀 테스트 100% 통과.
2. 좌표 변환과 FoV 수치 허용오차 충족.
3. 시각 baseline 변경은 독립 리뷰와 변경 사유를 포함.
4. `paper_like` fixture와 생성 명령, seed, 환경 버전이 저장됨.
5. 논문 그림 근사치와 실제 논문 실험 데이터의 구분이 결과 문서에 명시됨.
6. 실패/제외 테스트가 있다면 마일스톤을 승인하지 않고 원인과 담당자를 기록함.

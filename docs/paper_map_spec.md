# SCoPP 논문형 맵 요구사항 초안

## 목적과 근거

첫 마일스톤인 맵 모델·격자화·시각화의 범위를 SCoPP 원 논문에 맞춰 한정한다. 1차 근거는 Collins et al., *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas*, arXiv:2103.14709v1 (2021)이다.

- **사실**: 논문이 직접 명시한다.
- **추론**: 논문 명세로부터 도출되지만 직접 명시되지는 않는다.
- **가정**: 재현 가능한 구현을 위해 프로젝트가 결정해야 한다.

공식 원문: <https://arxiv.org/abs/2103.14709> (PDF: <https://arxiv.org/pdf/2103.14709>)

## 현재 실험 범위

실험은 건물 내 실험실에서 수행하므로 입력은 미터 단위 로컬 Cartesian `(x, y)`로
제한한다. 논문의 위·경도 변환 단계는 논문 분석 기록으로만 남기고 구현 및 검증
범위에서 제외한다. SCoPP 재현은 Cartesian 변환 이후의 pseudo-discretization,
clustering, conflict auction 및 path planning 단계를 대상으로 한다.

## 검증된 요구사항

| ID | 요구사항 | 분류 | 논문 근거 |
|---|---|---|---|
| MAP-01 | 2차원 비볼록 AOI를 표현한다. | 사실 | Sec. I, p.1; Sec. II, p.2 |
| MAP-02 | AOI 경계의 위도·경도 정점열을 입력받는다. | 사실 | Sec. III, Sec. III-A, pp.2–3 |
| MAP-03 | 로봇 수와 서로 다를 수 있는 초기 위치를 입력받는다. | 사실 | Sec. I, p.1; Fig. 1 설명, Sec. III-A |
| MAP-04 | 지리 좌표를 1 단위가 1 m인 Cartesian 좌표로 변환한다. | 사실 | Sec. III-A, Eqs. (1)–(2), p.3; 평균 지구 반지름 6,371 km |
| MAP-05 | AOI를 동일 폭의 정사각 셀로 된 pseudo-discrete 공간으로 변환한다. | 사실 | Sec. III-B, p.3; Fig. 1 Step 2 |
| MAP-06 | 셀 폭은 `W_k = 2 h tan(F/2)`이다. `h`는 지상고, `F`는 하향 카메라 FoV이다. | 사실 | Sec. III, pp.2–3; Sec. III-B |
| MAP-07 | 로봇이 셀 중심에 도달하면 그 셀을 관측한 것으로 간주한다. | 사실 | Sec. III 및 III-B, p.3 |
| MAP-08 | 셀 둘레를 균일 간격의 점들로 표현한다. | 사실 | Fig. 1 Step 2; Sec. III-B, p.3 |
| MAP-09 | AOI 내부 no-fly/geofenced zone을 표현하고 계산에서 제외한다. | 사실(기능 수준) | Abstract; Sec. I–II; Fig. 2(a), p.5 |
| MAP-10 | 시각화에서 AOI, no-fly zone, 경계 정점을 구분한다. | 사실+추론 | Fig. 2, p.5가 붉은 no-fly zone과 polygon marker를 표시하지만 렌더러 API는 명시하지 않음 |
| MAP-11 | 논문 실험 fixture로 약 `1.012 km²`, `3.436 km²` AOI를 지원한다. | 사실 | Sec. IV-A, p.5; 일반 입력 제한이 아님 |

## 입력 모델 초안

YAML/JSON 파일 포맷은 논문 명세가 아닌 **프로젝트 가정**이다. 논리 스키마는 다음 필드를 갖는다.

- `coordinate_system`: `WGS84`
- `aoi.vertices_latlon`: `[[lat, lon], ...]`
- `no_fly_zones`: zero or more polygon vertex lists
- `robots[].id`, `robots[].initial_position_latlon`
- `sensor.altitude_m`, `sensor.fov_deg`

검증 정책:

- AOI는 최소 3개 정점의 simple polygon이어야 한다(**가정**).
- 순서는 논문 표현대로 `(latitude, longitude)`로 고정한다.
- `altitude_m > 0`, `0 < fov_deg < 180`이어야 한다(**가정**).
- 삼각함수 적용 전에 degree를 radian으로 변환한다(**추론**).
- Cartesian 거리와 셀 폭의 단위는 meter다.

## 격자화와 포함 판정

논문이 확정하는 범위는 동일 폭 정사각 셀, 셀 중심 관측, 균일한 둘레 표본점까지다. 다음은 논문에 정의되지 않았다.

1. AOI 경계에 걸친 셀을 포함할지, 중심이 내부인 셀만 포함할지
2. no-fly zone 경계에 닿는 셀의 제외 기준
3. polygon winding order와 self-intersection 처리
4. 둘레 표본점의 정확한 간격과 모서리 중복 제거
5. 격자 원점, 축 방향 및 bounding box 정렬

프로젝트에서 확정한 기본 정책은 `area(cell footprint ∩ AOI) > 0`인 모든 셀을 포함하고,
`area(cell footprint ∩ no-fly-zone) > 0`인 셀은 비행 가능 집합에서 제외하는 것이다.
점 또는 선 접촉처럼 교집합 면적이 0인 셀은 포함하지 않는다. 경계 cell에는 전체
footprint와 `coverage_geometry = footprint ∩ AOI`를 함께 보존한다. 이는 AOI 누락을
방지하기 위한 **프로젝트 정책이며 논문 사실이 아니다**.

## 좌표 변환의 불확실성

논문은 Haversine Eqs. (1)–(2)와 지리↔Cartesian 변환을 명시하지만 다음은 불명확하다.

- Cartesian 원점과 동/서·남/북 부호
- 거리 두 개를 x/y 성분으로 분해하는 절차
- Eq. (5)의 변환 행렬 `C`와 bounds vector `G` 구성

따라서 round-trip 오차와 축 방향을 테스트하되 특정 구현을 곧바로 “논문 그대로”라고 주장하면 안 된다. AOI 기준점을 명시한 국소 tangent-plane 근사를 쓰거나 저자 공식 코드를 확인해야 한다.

## 시각화 수용 기준

- AOI 외곽선과 비볼록성을 식별할 수 있다.
- no-fly zone은 별도 색/채움으로 표시한다.
- 유효/제외 셀, 중심, 둘레 표본점을 선택적으로 표시한다.
- 로봇 초기 위치와 ID를 표시한다.
- 축 단위는 degree 또는 meter로 명시한다.
- Fig. 2 이미지에서 역추정한 맵은 “형상 근사”로 표시하며 실제 실험 좌표라고 주장하지 않는다.

## 최소 테스트

- `W_k`가 논문 식과 일치한다.
- 알려진 위·경도 쌍의 Haversine 거리가 meter 단위 기대값과 일치한다.
- 비볼록 AOI의 concavity 외부 셀과 no-fly zone 충돌 셀이 정책대로 제외된다.
- 경계 판정, 셀 ID 및 셀 중심 순서가 결정적이다.
- 둘레 점 간격과 모서리 중복 정책이 명세와 일치한다.
- 지리→Cartesian→지리 round trip 허용 오차가 문서화된다.

## AGENTS.md 보정 사항

- 복수 no-fly polygon은 합리적이지만 논문은 입력 자료구조를 명시하지 않으므로 **구현 가정**이다.
- “불연속 영역”은 no-fly/geofenced zone 의미로는 일치한다. 서로 분리된 복수 AOI component 지원은 명시되지 않았다.
- 유효/제외 셀의 정확한 polygon-cell 판정 규칙은 논문에 없다.
- YAML/JSON 스키마는 재현성 설계이며 논문 요구사항이 아니다.
- `W = 2h tan(F/2)`는 논문과 일치한다. 실험 카메라는 `18 × 14°` FoV인데 정사각 셀 식에 어느 성분을 썼는지는 불명확하다(Sec. IV-A, p.5).

## 미해결 확인 항목

1. 저자 공식 저장소 `adamslab-ub/SCoPP`에서 셀 포함 기준, perimeter 간격, 변환 원점과 축을 확인한다.
2. Fig. 2의 small/medium/large 정점 좌표가 공식 저장소에 있는지 확인한다.
3. `18 × 14°` 중 정사각 셀 폭에 사용한 `F`를 확인한다.
4. no-fly zone이 polygon hole인지 별도 polygon 목록인지 확인한다.
5. 본문은 medium/large 면적만 제시하므로 small map의 정확 면적과 좌표를 확인한다.

해결 전 관련 선택은 “논문과 동일”이 아니라 “재현을 위한 가정”으로 기록한다.

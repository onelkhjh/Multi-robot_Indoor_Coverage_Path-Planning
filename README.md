# SCoPP 논문 재현 / SCoPP Paper Reproduction

## 한국어

### 프로젝트 목적

이 저장소는 Collins et al.의 논문 *Scalable Coverage Path Planning of
Multi-Robot Teams for Monitoring Non-Convex Areas*에서 제안한 SCoPP를
재현하는 것을 우선 목표로 한다.

현재 실험 환경은 건물 내 실험실이다. 모든 지도 좌표는 미터 단위의 로컬 Cartesian
좌표 `[x, y]`를 사용하며 위도·경도 변환은 구현 범위에서 제외한다. 논문의 좌표 변환
이후 단계인 격자화, 영역 분할, conflict 경매 및 coverage path planning을 구현한다.

### 구현된 파이프라인

```text
실내 AOI 및 no-fly zone 입력
  → FoV 기반 정사각 cell 생성
  → Lloyd clustering
  → conflict cell 탐지 및 greedy auction
  → KD-tree nearest-neighbor coverage path
  → 실험 지표 및 확장성 평가
```

1. 지도와 격자화
   - 비볼록 AOI, no-fly zone 및 노드 시작 위치를 YAML/JSON으로 입력한다.
   - 논문 식 `W = 2h tan(F/2)`로 cell 폭을 계산한다.
   - `paper_center`는 셀 중심 기반 정책이고, `any_overlap`은 AOI 누락을 방지하기
     위한 임의 지형 연구 확장이다.
2. 영역 분할
   - cell perimeter 표본을 Lloyd 방식으로 clustering한다.
   - 기본 수렴 허용오차는 `W/8`, 최대 반복 횟수는 10회다.
   - 여러 cluster의 perimeter 표본을 갖는 cell을 conflict cell로 판정한다.
3. Conflict 경매
   - 비충돌 cell은 해당 cluster에 바로 할당한다.
   - conflict cell은 `현재 cell 수 + B × d0`가 가장 작은 노드에 순차 할당한다.
   - 공식 코드와 동일하게 `d0`를 cell 폭 단위로 반올림하며 기본값은 `B=0.5`다.
4. Coverage path planning
   - 각 노드는 시작 위치에서 가장 가까운 미방문 cell 중심을 반복 선택한다.
   - 2차원 KD-tree nearest-neighbor를 사용한다.
   - 공식 구현과의 정합성을 위해 마지막에 시작점으로 복귀한다.
5. 실험 평가
   - 노드별 cell 수와 이동거리, workload 편차, makespan, 전체 이동거리 및 단계별
     계산시간을 JSON으로 기록한다.
   - 노드 수에 따른 확장성 결과를 CSV와 그래프로 생성한다.

### 설치와 실행

Python 3.11 이상을 사용한다.

```powershell
python -m pip install -e ".[test]"
python -m pytest
```

지도 렌더링:

```powershell
python scripts/render_map.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab.png
```

영역 할당과 coverage path 생성:

```powershell
python scripts/plan_map.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab_plan.png
```

단일 실험 지표 생성:

```powershell
python scripts/run_experiment.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab_metrics.json
```

노드 수 확장성 평가:

```powershell
python scripts/run_scaling.py examples/maps/indoor_lab.yaml --output artifacts/indoor_scaling.csv --plot artifacts/indoor_scaling.png
```

인터랙티브 경로 할당 UI 생성:

```powershell
python scripts/build_path_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_ui.html
```

생성된 `artifacts/path_ui.html`을 브라우저에서 열면 노드별 영역과 경로를 선택하고
방문 순서를 재생할 수 있다.

### 현재 실내 예제 결과

- 유효 cell: 109개
- 노드: 4개
- conflict cell: 15개
- 노드별 할당 cell: `26, 28, 28, 27`
- 시작점 복귀를 포함한 makespan 거리: 약 `35.032 m`
- 테스트: 28개

실행시간은 시스템 상태에 따라 달라지므로 새 실험마다 다시 측정해야 한다.

### 논문·공식 코드와의 차이

현재 clustering은 재현성을 위해 결정적인 full-batch Lloyd 방식과 노드 시작점 초기화를
사용한다. 저자 공식 코드는 stochastic `MiniBatchKMeans`로 먼저 cluster를 만든 뒤
cluster와 로봇 시작점을 연결한다. 또한 공식 코드는 cell 폭을 정수이자 짝수로 만들고
perimeter 간격을 3 m로 고정하지만, 이 설정은 1 m 미만 cell을 사용하는 실내 실험에
적합하지 않아 현재 구현에서는 부동소수점 cell 폭과 `W/8` 간격을 유지한다.

따라서 현재 결과는 SCoPP 논문을 기반으로 한 결정적 실내 구현이며 공식 코드와
byte-for-byte 동일한 결과를 주장하지 않는다. 자세한 검증 내용은
[`docs/official_parity_audit.md`](docs/official_parity_audit.md)에 정리되어 있다.
한국어 검증 문서는
[`docs/official_parity_audit.ko.md`](docs/official_parity_audit.ko.md)에서 확인할 수 있다.

## English

### Purpose

This repository prioritizes a reproducible indoor implementation of Collins et
al., *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring
Non-Convex Areas* (SCoPP). Maps use local Cartesian `[x, y]` coordinates in
metres; geographic conversion is outside the current laboratory scope.

### Implemented stages

- polygonal AOI and no-fly-zone loading;
- camera footprint `W = 2h tan(F/2)` and square-cell discretization;
- deterministic Lloyd clustering with `W/8` tolerance and at most 10 iterations;
- conflict detection and the greedy `cell count + B × d0` auction;
- KD-tree nearest-neighbor coverage routes returning to each node start;
- JSON experiment metrics and CSV/PNG node-count scaling reports.

### Quick start

```powershell
python -m pip install -e ".[test]"
python -m pytest
python scripts/plan_map.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab_plan.png
python scripts/run_experiment.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab_metrics.json
python scripts/run_scaling.py examples/maps/indoor_lab.yaml --output artifacts/indoor_scaling.csv --plot artifacts/indoor_scaling.png
```

### Reproduction boundary

The implementation follows the paper pipeline but deliberately retains
floating-point indoor cell widths and deterministic full-batch Lloyd clustering.
The public author code uses integer/even cell widths, a fixed 3 m perimeter
interval, and stochastic `MiniBatchKMeans`. See
[`docs/official_parity_audit.md`](docs/official_parity_audit.md) for the detailed
parity audit.

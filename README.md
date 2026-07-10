# Multi-robot Indoor Coverage Path Planning

## 한국어

이 저장소는 Leighton Collins et al.의 논문 *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas* (arXiv:2103.14709)과 저자 공식 코드를 기준선으로 두고, 같은 조건에서 더 나은 KPI를 만드는 방향으로 진행한다.

기준선으로 유지하는 범위는 clustering, auction, coverage path planning이다. 이 세 단계는 논문 재현의 기준으로 남겨두되, 실제 작업 초점은 실내 비행에 더 적합한 경로와 지표를 만드는 쪽에 둔다.

이 프로젝트는 Multi-robot Indoor Coverage Path Planning으로 정리한다. 따라서 direct-distance와 executable-distance를 섞지 않고, 동일한 맵과 동일한 할당, 동일한 제약 조건에서만 비교한다.

## 핵심 방향

- baseline reference: SCoPP 논문 + 공식 코드
- comparison focus: 같은 상태에서의 KPI 비교
- optimization focus: 실내 비행에 더 적합한 경로와 지표
- reporting discipline: direct-distance와 executable-distance를 섞지 않음
- reference retention: clustering, auction, coverage path planning은 기준선으로 유지

## 현재 보관 중인 핵심 결과물

- `artifacts/path_planner_exec_only_v1.json`
- `artifacts/path_planner_exec_only_v1.png`
- `artifacts/executable_kpi_result.md`
- `artifacts/indoor_lab.png`
- `artifacts/indoor_lab_plan.png`
- `artifacts/indoor_lab_metrics.json`
- `artifacts/paper_like.png`

## 생성 방법

UI는 Python 스크립트가 생성하고, 원본 템플릿은 `src/scopp/ui/`에 둔다.

```powershell
python -m pip install -e ".[test]"
python -m pytest
python scripts/build_path_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_ui.html
python scripts/build_progress_ui.py --output artifacts/progress_ui.html
python scripts/build_path_comparison_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_comparison_ui.html --seed 0 --bias 0.5
python scripts/compare_path_planners.py examples/maps/indoor_lab.yaml --seed 0 --bias 0.5 --output artifacts/path_planner_exec_only_v1.json --plot artifacts/path_planner_exec_only_v1.png
```

## 실행 기준 비교 결과

핵심 비교 결과는 `artifacts/path_planner_exec_only_v1.png` 이다. 이 결과는 동일한 `grid-adjacent executable` 모델과 no-fly 차단 조건에서 Metric-TSP와 public-code NN을 비교한다.

요약 문서는 `artifacts/executable_kpi_result.md` 에 있다.

## 서브 에이전트

서브 에이전트 역할과 사용 규칙은 [docs/subagents.md](docs/subagents.md) 에 정리되어 있다.

## 참고

- `path_ui.html`, `progress_ui.html`, `path_comparison_ui.html` 는 Python 스크립트가 생성하는 UI 템플릿이다.
- 최종 KPI 보고는 direct-distance 숫자를 사용하지 않는다.

---

## English

This repository uses the SCoPP paper *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas* (arXiv:2103.14709) and the official author code as the baseline reference, while targeting better KPI under the same conditions and optimizing for indoor flight.

The baseline scope stays focused on clustering, auction, and coverage path planning. Those stages remain the reference behavior for reproduction, but the main project emphasis is on routes and metrics that are more suitable for indoor flight.

The project is framed as Multi-robot Indoor Coverage Path Planning. Direct-distance and executable-distance are never mixed; comparisons are always made under the same map, the same allocation, and the same constraints.

## Core direction

- baseline reference: SCoPP paper + official code
- comparison focus: KPI under the same state
- optimization focus: paths and metrics better suited for multi-robot indoor flight
- reporting discipline: do not mix direct-distance and executable-distance
- reference retention: clustering, auction, and coverage path planning stay as baseline behavior

## Current checked-in artifacts

- `artifacts/path_planner_exec_only_v1.json`
- `artifacts/path_planner_exec_only_v1.png`
- `artifacts/executable_kpi_result.md`
- `artifacts/indoor_lab.png`
- `artifacts/indoor_lab_plan.png`
- `artifacts/indoor_lab_metrics.json`
- `artifacts/paper_like.png`

## Run

```powershell
python -m pip install -e ".[test]"
python -m pytest
python scripts/build_path_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_ui.html
python scripts/build_progress_ui.py --output artifacts/progress_ui.html
python scripts/build_path_comparison_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_comparison_ui.html --seed 0 --bias 0.5
python scripts/compare_path_planners.py examples/maps/indoor_lab.yaml --seed 0 --bias 0.5 --output artifacts/path_planner_exec_only_v1.json --plot artifacts/path_planner_exec_only_v1.png
```

## Exec-only comparison result

The main comparison artifact is `artifacts/path_planner_exec_only_v1.png`. It compares Metric-TSP and public-code NN under the same `grid-adjacent executable` model with no-fly blocking.

The summary report is `artifacts/executable_kpi_result.md`.

## Sub-agents

The sub-agent roles and usage rules are documented in [docs/subagents.md](docs/subagents.md).

## Notes

- `path_ui.html`, `progress_ui.html`, and `path_comparison_ui.html` are Python-generated UI templates.
- Final KPI reporting does not use direct-distance numbers.

# Multi-robot Indoor Coverage Path Planning

이 저장소는 SCoPP 논문 *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas*와 저자 공식 코드를 기준선으로 유지하면서, 동일한 맵·할당·제약에서 실내 다중 로봇 커버리지 KPI를 개선하는 프로젝트다.

## 기본 프로필

- Clustering: `official_minibatch` — SCoPP 공식 기준선
- Path planning: `approx_metric_tsp` — 현재 운영 및 KPI 개선 기본값
- Baseline path: `paper_nn` — SCoPP/public-code 비교용 기준선
- Legacy exact path: `legacy_exact_tsp` — 20개 이하 소규모 문제의 회귀 검증 및 optimality-gap 측정용

`approx_metric_tsp`는 valid-cell 4-neighbor 그래프의 최단거리로 metric closure를 만들고, deterministic cheapest insertion과 2-opt로 방문 순서를 계산한다. 모든 로봇에 같은 근사해법을 적용하며 셀 개수에 따라 exact 해법으로 자동 전환하지 않는다.

## 비교 원칙

- 같은 맵, clustering/allocation, seed, auction bias 및 비행 제약을 사용한다.
- SCoPP clustering, conflict auction, `paper_nn` 경로는 기준선으로 보존한다.
- 개선 경로와 기준선 결과를 별도 프로필과 산출물로 관리한다.
- 셀 중심 direct distance와 실제 제약을 반영한 executable distance를 분리해 보고한다.
- 최종 KPI는 valid-cell 이동 및 no-fly 차단을 적용한 executable distance를 중심으로 평가한다.

## 현재 KPI

동일한 `official_minibatch`, `seed=0`, `auction_bias=0.5` 조건에서 `approx_metric_tsp`를 public-code NN과 비교한 결과:

| KPI | Approx Metric-TSP | Public-code NN | 개선 |
|---|---:|---:|---:|
| Executable makespan | 43.266 m | 50.656 m | 14.59% |
| Executable total distance | 147.184 m | 167.506 m | 12.13% |

상세 결과는 [executable KPI report](artifacts/executable_kpi_result.md)에 있다.

## 핵심 산출물

- `artifacts/path_planner_exec_only_v1.json`
- `artifacts/path_planner_exec_only_v1.png`
- `artifacts/executable_kpi_result.md`
- `artifacts/path_ui.html`
- `artifacts/path_comparison_ui.html`
- `artifacts/indoor_lab_metrics.json`

## 실행

```powershell
python -m pip install -e ".[test]"
python -m pytest

# 기본값: official_minibatch + approx_metric_tsp
python scripts/plan_map.py examples/maps/indoor_lab.yaml
python scripts/run_experiment.py examples/maps/indoor_lab.yaml --output artifacts/indoor_lab_metrics.json
python scripts/build_path_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_ui.html

# 동일 할당에서 개선 경로와 SCoPP NN 기준선 비교
python scripts/build_path_comparison_ui.py examples/maps/indoor_lab.yaml --output artifacts/path_comparison_ui.html --seed 0 --bias 0.5
python scripts/compare_path_planners.py examples/maps/indoor_lab.yaml --seed 0 --bias 0.5 --output artifacts/path_planner_exec_only_v1.json --plot artifacts/path_planner_exec_only_v1.png
```

기준선 재현이 필요하면 명시적으로 `--path-profile paper_nn`을 사용한다. Exact 검증은 `--path-profile legacy_exact_tsp`로 실행하며 로봇별 target이 20개를 넘으면 실패하는 것이 정상이다.

## English summary

The SCoPP paper and official code remain the reproduction baseline. The active indoor route planner is now `approx_metric_tsp`, using metric closure over the valid-cell graph followed by deterministic cheapest insertion and 2-opt. `paper_nn` remains available only as the SCoPP/public-code path baseline, while `legacy_exact_tsp` is retained for small-instance regression and optimality-gap checks. Direct and executable distances are reported separately under fixed map, allocation, and constraints.

## Attribution and third-party software

This project references the SCoPP paper and the authors' MIT-licensed official implementation, and adds indoor coverage-planning adaptations for this repository's use cases.

- Upstream reference: [adamslab-ub/SCoPP](https://github.com/adamslab-ub/SCoPP)
- Paper: Collins et al., *Scalable Coverage Path Planning of Multi-Robot Teams for Monitoring Non-Convex Areas*, ICRA 2021, arXiv:2103.14709
- Retained reference behavior: clustering, conflict-cell auction, and `paper_nn`
- Project extensions: indoor map policies, no-fly handling, executable 4-neighbor transit, `approx_metric_tsp`, KPI reporting, and experiment UIs

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency and attribution details.

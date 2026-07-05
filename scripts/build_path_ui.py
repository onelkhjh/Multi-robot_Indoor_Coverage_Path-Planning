"""Build a standalone interactive HTML UI for inspecting SCoPP assignments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scopp import allocate_conflict_cells, cluster_map, discretize_map, load_map, plan_coverage_paths


HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SCoPP 경로 할당 검사기</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#121a2d;--line:#26334f;--text:#eef3ff;--muted:#91a0bd;--accent:#5eead4}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 30% 0,#172443,#0b1020 55%);color:var(--text);font:14px/1.5 system-ui,sans-serif}
header{padding:20px 24px 12px;display:flex;justify-content:space-between;align-items:end;gap:20px}h1{font-size:22px;margin:0}header p{margin:3px 0 0;color:var(--muted)}
.badge{border:1px solid #2c806f;background:#103c39;color:#8ff5df;padding:5px 9px;border-radius:999px;font-weight:700}
main{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:14px;padding:0 24px 24px;min-height:calc(100vh - 90px)}
.panel{background:linear-gradient(180deg,#131d33eF,#0e1629eF);border:1px solid var(--line);border-radius:14px;box-shadow:0 18px 50px #0005}
.map-wrap{padding:12px;display:flex;flex-direction:column;min-height:650px}.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:5px 5px 12px}
button,select,input{accent-color:var(--accent)}button,select{background:#17243d;color:var(--text);border:1px solid #344461;border-radius:8px;padding:7px 10px}button:hover{border-color:var(--accent)}button:focus-visible{outline:2px solid var(--accent)}
.toolbar label{display:flex;align-items:center;gap:5px;color:#cbd5e1}.spacer{flex:1}.step{font-variant-numeric:tabular-nums;color:var(--muted)}
svg{width:100%;height:100%;min-height:570px;background:#09101e;border:1px solid #22304b;border-radius:10px}.aoi{fill:#111b30;stroke:#d8e4ff;stroke-width:.06}.nofly{fill:#f43f5e55;stroke:#fb7185;stroke-width:.05}.cell{stroke:#ffffff30;stroke-width:.018;transition:opacity .15s}.route{fill:none;stroke-width:.08;stroke-linecap:round;stroke-linejoin:round;opacity:.88}.route.dim,.cell.dim,.node.dim{opacity:.08}.node{stroke:#08101e;stroke-width:.06}.visited{stroke:#fff;stroke-width:.08}.cursor{fill:#fff;stroke:#08101e;stroke-width:.06}
aside{display:flex;flex-direction:column;gap:12px}.section{padding:14px}.section h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#a9b7d1;margin:0 0 10px}
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px}.metric{padding:10px;background:#0c1426;border:1px solid #253553;border-radius:9px}.metric b{display:block;font-size:18px}.metric span{font-size:11px;color:var(--muted)}
.node-row{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;padding:9px 8px;border-radius:9px;border:1px solid transparent;cursor:pointer}.node-row:hover,.node-row.active{background:#18243d;border-color:#34486d}.dot{width:11px;height:11px;border-radius:50%}.node-row small{color:var(--muted)}.movement{margin-top:3px;color:#d9e5fa;font-size:11px;font-variant-numeric:tabular-nums}.progressbar{height:3px;background:#26334f;border-radius:3px;margin-top:5px;overflow:hidden}.progressbar i{display:block;height:100%;width:0;background:var(--accent)}
.legend{display:flex;gap:14px;color:var(--muted);font-size:12px}.key{display:flex;gap:5px;align-items:center}.swatch{width:12px;height:12px;border-radius:3px}.warn{color:#fecdd3;background:#3a1622;border:1px solid #7f1d35;padding:9px;border-radius:8px;font-size:12px}
@media(max-width:900px){main{grid-template-columns:1fr}.map-wrap{min-height:540px}svg{min-height:450px}}
</style>
</head>
<body>
<header><div><h1>SCoPP 경로 할당 검사기</h1><p id="subtitle"></p></div><span class="badge">결정적 실행</span></header>
<main>
<section class="panel map-wrap">
<div class="toolbar">
 <button id="play" data-testid="play">▶ 재생</button><button id="reset" data-testid="reset">↺ 초기화</button>
 <label>속도 <select id="speed"><option value="0.025">느림</option><option value="0.06" selected>보통</option><option value="0.14">빠름</option></select></label>
 <label><input id="showCells" type="checkbox" checked>영역</label><label><input id="showRoutes" type="checkbox" checked>경로</label><label><input id="showNoFly" type="checkbox" checked>금지 구역</label>
 <span class="spacer"></span><span class="step" id="step">0 / 0</span>
</div>
<svg id="map" role="img" aria-label="노드별 할당 영역과 coverage path"></svg>
</section>
<aside>
 <section class="panel section"><h2>실행 요약</h2><div class="metrics" id="metrics"></div></section>
 <section class="panel section"><h2>노드별 할당</h2><div id="nodes"></div></section>
 <section class="panel section"><h2>현재 이동 상태</h2><div id="movement">재생을 시작하면 노드의 위치와 다음 목표가 표시됩니다.</div></section>
 <section class="panel section"><h2>표시 정보</h2><div class="legend"><span class="key"><i class="swatch" style="background:#f43f5e88"></i>no-fly</span><span class="key"><i class="swatch" style="background:#fff"></i>현재 위치</span></div><p class="warn">선은 논문식 방문 순서입니다. 셀 사이 직선 구간의 물리적 장애물 회피는 아직 적용되지 않았습니다.</p></section>
</aside>
</main>
<script>
const D=__DATA__;
const C=['#38bdf8','#fb923c','#4ade80','#f87171','#c084fc','#facc15','#2dd4bf','#f472b6'];
const svg=document.querySelector('#map'),NS='http://www.w3.org/2000/svg';let selected=null,step=0,timer=null;
const allPoints=[...D.aoi,...D.noFly.flat(),...D.cells.flatMap(c=>c.vertices),...D.nodes.flatMap(n=>n.trajectory)];
const xs=allPoints.map(p=>p[0]),ys=allPoints.map(p=>p[1]),pad=D.cellWidth*.8,minX=Math.min(...xs)-pad,maxX=Math.max(...xs)+pad,minY=Math.min(...ys)-pad,maxY=Math.max(...ys)+pad;
svg.setAttribute('viewBox',`${minX} ${-maxY} ${maxX-minX} ${maxY-minY}`);
const E=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e};const pts=a=>a.map(p=>`${p[0]},${-p[1]}`).join(' ');
svg.append(E('polygon',{points:pts(D.aoi),class:'aoi'}));const noFly=E('g',{id:'noFly'});D.noFly.forEach(z=>noFly.append(E('polygon',{points:pts(z),class:'nofly'})));svg.append(noFly);
const cells=E('g',{id:'cells'});D.cells.forEach(c=>{const e=E('polygon',{points:pts(c.vertices),fill:C[c.owner%C.length],class:'cell',id:`cell-${c.id}`,'data-owner':c.owner});cells.append(e)});svg.append(cells);
const routes=E('g',{id:'routes'});D.nodes.forEach(n=>{routes.append(E('polyline',{points:pts(n.trajectory),stroke:C[n.index%C.length],class:'route',id:`route-${n.index}`,'data-owner':n.index}))});svg.append(routes);
const nodeLayer=E('g',{id:'nodeLayer'});D.nodes.forEach(n=>{nodeLayer.append(E('circle',{cx:n.start[0],cy:-n.start[1],r:D.cellWidth*.18,fill:C[n.index%C.length],class:'node','data-owner':n.index}));});svg.append(nodeLayer);const cursorLayer=E('g',{id:'cursorLayer'});D.nodes.forEach(n=>cursorLayer.append(E('circle',{id:`cursor-${n.index}`,r:D.cellWidth*.15,class:'cursor',fill:C[n.index%C.length]})));svg.append(cursorLayer);
document.querySelector('#subtitle').textContent=`${D.name} · ${D.cells.length} cells · ${D.nodes.length} nodes`;
const metricData=[['Cell',D.cells.length],['Conflict',D.conflicts],['Makespan',`${D.makespan.toFixed(2)} m`],['총 거리',`${D.totalDistance.toFixed(2)} m`]];document.querySelector('#metrics').innerHTML=metricData.map(x=>`<div class="metric"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('');
document.querySelector('#nodes').innerHTML=D.nodes.map(n=>`<div class="node-row" data-testid="node-${n.index}" data-index="${n.index}"><i class="dot" style="background:${C[n.index%C.length]}"></i><div><b>${n.id}</b><br><small>${n.cells} cells · ${n.distance.toFixed(2)} m</small><div class="movement" id="node-status-${n.index}">대기 · (${n.start[0].toFixed(2)}, ${n.start[1].toFixed(2)})</div><div class="progressbar"><i id="bar-${n.index}"></i></div></div><span>${n.waypoints.length}</span></div>`).join('');
const maxSteps=Math.max(...D.nodes.map(n=>n.trajectory.length));
function applyFilter(){document.querySelectorAll('[data-owner]').forEach(e=>e.classList.toggle('dim',selected!==null&&+e.dataset.owner!==selected));document.querySelectorAll('.node-row').forEach(e=>e.classList.toggle('active',selected!==null&&+e.dataset.index===selected))}
function positionAt(n,t){const end=n.trajectory.length-1,clamped=Math.min(t,end),i=Math.floor(clamped),f=clamped-i,a=n.trajectory[i],b=n.trajectory[Math.min(i+1,end)];return {p:[a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f],i,f}}
function cumulative(n,t){const s=positionAt(n,t);let d=0;for(let i=1;i<=s.i;i++){const a=n.trajectory[i-1],b=n.trajectory[i];d+=Math.hypot(b[0]-a[0],b[1]-a[1])}if(s.f&&s.i<n.trajectory.length-1){const a=n.trajectory[s.i],b=n.trajectory[s.i+1];d+=Math.hypot(b[0]-a[0],b[1]-a[1])*s.f}return d}
function drawStep(){document.querySelectorAll('.visited').forEach(e=>e.classList.remove('visited'));const active=selected===null?D.nodes:D.nodes.filter(n=>n.index===selected);D.nodes.forEach(n=>{const isActive=active.some(a=>a.index===n.index),s=positionAt(n,step),p=s.p,cursor=document.querySelector(`#cursor-${n.index}`);cursor.setAttribute('cx',p[0]);cursor.setAttribute('cy',-p[1]);cursor.setAttribute('visibility',isActive?'visible':'hidden');if(isActive)n.cellIds.slice(0,Math.max(0,s.i-1)).forEach(id=>document.querySelector(`#cell-${id}`)?.classList.add('visited'));const returning=s.i>=n.trajectory.length-2&&step>0,target=s.i===0?'첫 번째 cell':returning?'시작점':n.cellIds[Math.min(s.i,n.cellIds.length-1)],dist=cumulative(n,step),pct=n.trajectory.length>1?Math.min(step,n.trajectory.length-1)/(n.trajectory.length-1)*100:100;document.querySelector(`#node-status-${n.index}`).textContent=`${returning?'복귀':step===0?'대기':'이동'} · (${p[0].toFixed(2)}, ${p[1].toFixed(2)}) · 다음 ${target} · ${dist.toFixed(2)} m`;document.querySelector(`#bar-${n.index}`).style.width=`${pct}%`});document.querySelector('#movement').innerHTML=active.map(n=>{const s=positionAt(n,step),p=s.p;return `<div style="margin:5px 0;color:${C[n.index%C.length]}"><b>${n.id}</b> — 구간 ${s.i}/${n.trajectory.length-1}, 위치 (${p[0].toFixed(2)}, ${p[1].toFixed(2)}), 누적 ${cumulative(n,step).toFixed(2)} m</div>`}).join('');document.querySelector('#step').textContent=`${step.toFixed(1)} / ${selected===null?maxSteps-1:D.nodes[selected].trajectory.length-1}`}
function stop(){if(timer){clearInterval(timer);timer=null}document.querySelector('#play').textContent='▶ 재생'}function play(){if(timer){stop();return}document.querySelector('#play').textContent='Ⅱ 일시정지';timer=setInterval(()=>{const limit=selected===null?maxSteps-1:D.nodes[selected].trajectory.length-1;if(step>=limit){step=limit;drawStep();stop();return}step=Math.min(limit,step+(+document.querySelector('#speed').value));drawStep()},50)}
document.querySelector('#play').onclick=play;document.querySelector('#reset').onclick=()=>{stop();step=0;drawStep()};document.querySelector('#speed').onchange=()=>{if(timer){stop();play()}};
document.querySelector('#showCells').onchange=e=>cells.style.display=e.target.checked?'':'none';document.querySelector('#showRoutes').onchange=e=>routes.style.display=e.target.checked?'':'none';document.querySelector('#showNoFly').onchange=e=>noFly.style.display=e.target.checked?'':'none';
document.querySelectorAll('.node-row').forEach(e=>e.onclick=()=>{selected=selected===+e.dataset.index?null:+e.dataset.index;step=0;stop();applyFilter();drawStep()});applyFilter();drawStep();
</script>
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("map_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/path_ui.html"))
    args = parser.parse_args()
    mapped = discretize_map(load_map(args.map_file))
    clustered = cluster_map(mapped)
    allocation = allocate_conflict_cells(mapped, clustered)
    plan = plan_coverage_paths(mapped, allocation)
    owners = dict(allocation.owner_by_cell)
    data = {
        "name": mapped.source.name,
        "cellWidth": mapped.cell_width_m,
        "aoi": mapped.source.aoi.exterior,
        "noFly": [zone.exterior for zone in mapped.source.no_fly_zones],
        "conflicts": len(allocation.auction_decisions),
        "makespan": plan.makespan_distance_m,
        "totalDistance": plan.total_distance_m,
        "cells": [{"id": c.id, "vertices": c.vertices, "owner": owners[c.id]} for c in mapped.cells],
        "nodes": [{"index": p.cluster_index, "id": p.node_id, "start": p.start, "cells": len(p.cell_ids), "distance": p.distance_m, "cellIds": p.cell_ids, "waypoints": p.waypoints, "trajectory": p.trajectory} for p in plan.paths],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()

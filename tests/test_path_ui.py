from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_path_ui_builds_standalone_html(tmp_path: Path) -> None:
    output = tmp_path / "ui.html"
    subprocess.run([sys.executable, str(ROOT / "scripts/build_path_ui.py"), str(ROOT / "examples/maps/indoor_lab.yaml"), "--output", str(output)], check=True)
    html = output.read_text(encoding="utf-8")
    assert "SCoPP 경로 할당 검사기" in html
    assert 'data-testid="play"' in html
    assert 'data-testid="node-${n.index}"' in html
    assert '"id": "node-01"' in html
    assert "Arbitrary indoor laboratory map" in html
    assert "__DATA__" not in html

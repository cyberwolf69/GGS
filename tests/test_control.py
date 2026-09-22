from pathlib import Path

import ggs.state as st


def test_pause_resume(tmp_path, monkeypatch):
    p = tmp_path / "control.json"
    monkeypatch.setattr(st, "CONTROL_FILE", p)
    monkeypatch.setattr(st, "RUNTIME", tmp_path)
    assert st.set_paused(True)["paused"] is True
    assert st.get_control()["paused"] is True
    assert st.set_paused(False)["paused"] is False

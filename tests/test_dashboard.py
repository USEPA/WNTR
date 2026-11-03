from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[1] / "ward" / "dashboard.py"


def test_preview_returns_network_and_comparable_pressure_series():  # validate that the /preview endpoint returns the expected junction IDs, network HTML, and sample pressure data
    from ward.prototype_api import app

    response = TestClient(app).get("/preview")

    assert response.status_code == 200
    data = response.json()
    assert data["junctions"][:2] == ["10", "15"]
    assert "Plotly.newPlot" in data["network_html"]
    assert "Junction: 10" in data["network_html"]
    assert data["time_hours"] == [0, 1, 2, 3]
    assert data["sample_pressures"] == {
        "baseline": [50, 50, 50, 50],
        "attack": [50, 15, 18, 50],
    }


def test_dashboard_loads_api_data_and_changes_selected_node(
    monkeypatch,
):  # validate that the dashboard loads API data and updates heading when a different node is selected
    from ward.prototype_api import app

    client = TestClient(app)
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: client.get("/preview"))

    page = AppTest.from_file(str(DASHBOARD)).run()

    assert not page.exception
    assert len(page.get("iframe")) == 1
    assert page.selectbox[0].value == "10"
    assert "10" in page.subheader[1].value
    assert page.dataframe[0].value["Attack (psi)"].tolist() == [50, 15, 18, 50]

    page.selectbox[0].select("15").run()

    assert not page.exception
    assert "15" in page.subheader[1].value
    assert page.dataframe[0].value["Attack (psi)"].tolist() == [50, 15, 18, 50]


def test_dashboard_explains_unavailable_api_and_can_retry(
    monkeypatch,
):  # validate that the dashboard shows an error message when the prototype API is unavailable and can recover when the API becomes available again
    def unavailable(url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "get", unavailable)
    page = AppTest.from_file(str(DASHBOARD)).run()

    assert not page.exception
    assert (
        page.error[0].value
        == "Cannot load sample data. Check that the prototype API is running, then reload."
    )
    assert not page.selectbox

    from ward.prototype_api import app

    client = TestClient(app)
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: client.get("/preview"))
    page.button[0].click().run()

    assert not page.exception
    assert not page.error
    assert len(page.get("iframe")) == 1
    assert page.selectbox[0].value == "10"

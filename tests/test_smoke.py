"""Smoke tests that run without a database (import + route wiring + scoring math)."""
from app.main import app
from app.models.enums import LeadColour
from app.services.scoring import colour_for


def test_app_imports_and_has_routes():
    paths = {r.path for r in app.routes}
    assert "/health" in paths
    assert any(p.startswith("/api/v1/projects") for p in paths)
    assert any("external" in p for p in paths)


def test_colour_thresholds():
    th = {"dark_green": 80, "green": 60, "yellow": 40}
    assert colour_for(95, th) == LeadColour.dark_green
    assert colour_for(65, th) == LeadColour.green
    assert colour_for(45, th) == LeadColour.yellow
    assert colour_for(10, th) == LeadColour.unqualified

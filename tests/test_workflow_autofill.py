"""Autofill steps in workflows: Pump Reagent, Stop Pumps, Read Level.

Pump Reagent mirrors the reservoir task operators already know: fill or empty
the station at a location, optionally with the second pump, the weigh station
and concurrent operation. The safety property carries over from the driver:
no pump outlives its step unless asked to, and none outlives the workflow.
"""
from __future__ import annotations

import pytest

from pybravo.workflow.executor import WorkflowExecutor, _build_task_params
from tests.test_autofill import _sim_bravo

STATION = 3  # _sim_bravo() puts the autofill station at location 3


def _chain(*nodes: tuple[str, dict]) -> dict:
    """Start -> nodes... -> End, linked by flow links."""
    spec = [("flow/Start", {}), *nodes, ("flow/End", {})]
    graph_nodes, links = [], []
    for i, (node_type, props) in enumerate(spec, start=1):
        graph_nodes.append({
            "id": i, "type": node_type, "properties": props,
            "inputs": [{"name": "flow", "type": -1, "link": i - 1 if i > 1 else None}],
            "outputs": [{"name": "flow", "type": -1, "links": [i] if i < len(spec) else []}],
        })
        if i < len(spec):
            links.append([i, i, 0, i + 1, 0, -1])
    return {"nodes": graph_nodes, "links": links}


def _loop(count: int, node: tuple[str, dict]) -> dict:
    """Start -> Loop(count) -body-> node ; Loop -done-> End."""
    node_type, props = node
    return {
        "nodes": [
            {"id": 1, "type": "flow/Start", "properties": {},
             "outputs": [{"name": "flow", "type": -1, "links": [1]}]},
            {"id": 2, "type": "flow/Loop", "properties": {"count": count},
             "inputs": [{"name": "flow", "type": -1, "link": 1}],
             "outputs": [{"name": "body", "type": -1, "links": [2]},
                         {"name": "done", "type": -1, "links": [3]}]},
            {"id": 3, "type": node_type, "properties": props,
             "inputs": [{"name": "flow", "type": -1, "link": 2}],
             "outputs": [{"name": "flow", "type": -1, "links": []}]},
            {"id": 4, "type": "flow/End", "properties": {},
             "inputs": [{"name": "flow", "type": -1, "link": 3}], "outputs": []},
        ],
        "links": [[1, 1, 0, 2, 0, -1], [2, 2, 0, 3, 0, -1], [3, 2, 1, 4, 0, -1]],
    }


def _driver(bravo):
    return bravo._autofill_driver("autofill", require_enabled=False)


async def _run(bravo, graph) -> WorkflowExecutor:
    executor = WorkflowExecutor(bravo, graph, preview_animation=False)
    await executor.execute()
    return executor


def _fill(**overrides) -> tuple[str, dict]:
    props = {"location": STATION, "reservoir_mode": "fill", "pump_speed_pct": 50,
             "pump_on_time_s": 0.3, "allow_concurrent": False}
    props.update(overrides)
    return ("accessory/PumpReagent", props)


def test_pump_reagent_params():
    params = _build_task_params("accessory/PumpReagent", {
        "location": 3, "reservoir_mode": "empty", "pump_speed_pct": 80, "pump_on_time_s": 7,
        "how_often": 2, "allow_concurrent": True, "run_second_pump": True,
        "second_pump_speed_pct": 30, "use_weigh_station": True,
        "action_threshold_pct": 60, "stop_threshold_pct": 10,
    })
    assert params == {
        "location": 3, "reservoir_mode": "empty", "pump_speed_pct": 80.0, "pump_on_time_s": 7.0,
        "allow_concurrent": True, "run_second_pump": True, "second_pump_speed_pct": 30.0,
        "use_weigh_station": True, "action_threshold_pct": 60.0, "stop_threshold_pct": 10.0,
    }


def test_mix_and_aspirate_pass_the_height_above_the_bottom():
    mix = _build_task_params("liquid/Mix", {"location": 3, "volume": 50, "cycles": 4,
                                            "distance_from_bottom": 2.5})
    assert mix["aspirate_distance"] == 2.5 and mix["mix_cycles"] == 4
    asp = _build_task_params("liquid/Aspirate", {"location": 3, "volume": 50, "distance_from_bottom": 1.5})
    assert asp["distance_from_bottom"] == 1.5


@pytest.mark.asyncio
async def test_fill_waits_for_the_pumps_then_read_level_stores_the_level():
    bravo = _sim_bravo()
    executor = await _run(bravo, _chain(
        _fill(),
        ("accessory/ReadLevel", {"location": STATION, "store_as": "level"}),
    ))
    assert not _driver(bravo).is_running
    assert executor._vars["level"] > 0


@pytest.mark.asyncio
async def test_pumping_publishes_the_level_for_the_3d_view():
    bravo = _sim_bravo()
    events = []

    async def on_event(event):
        events.append(event)

    executor = WorkflowExecutor(bravo, _chain(_fill(pump_on_time_s=1.0)), on_event=on_event,
                                preview_animation=False)
    await executor.execute()
    levels = [e["level_pct"] for e in events if e.get("type") == "workflow:autofill_level"]
    assert all(e["location"] == STATION for e in events if e.get("type") == "workflow:autofill_level")
    assert len(levels) >= 3 and levels[-1] > levels[0]


@pytest.mark.asyncio
async def test_weigh_station_stops_the_fill_at_the_stop_threshold():
    bravo = _sim_bravo()
    result = await bravo.pump_reagent(
        STATION, reservoir_mode="fill", pump_speed_pct=50, pump_on_time_s=30,
        use_weigh_station=True, action_threshold_pct=50, stop_threshold_pct=5,
    )
    assert result["status"] == "done"
    assert 5 <= result["end_level_pct"] < 15  # stopped long before the 30 s timeout
    assert not _driver(bravo).is_running


@pytest.mark.asyncio
async def test_weigh_station_skips_a_fill_when_already_above_the_action_threshold():
    bravo = _sim_bravo()  # empty tray reads 0 %
    result = await bravo.pump_reagent(
        STATION, reservoir_mode="fill", pump_on_time_s=5,
        use_weigh_station=True, action_threshold_pct=0, stop_threshold_pct=50,
    )
    assert result["status"] == "skipped"
    assert not _driver(bravo).is_running


@pytest.mark.asyncio
async def test_empty_mode_with_second_pump_runs_both_with_their_speeds(monkeypatch):
    bravo = _sim_bravo()
    calls = []
    driver = _driver(bravo)
    real = driver.run_pumps
    monkeypatch.setattr(driver, "run_pumps", lambda *a, **k: (calls.append((a, k)), real(*a, **k))[1])

    await bravo.pump_reagent(STATION, reservoir_mode="empty", pump_speed_pct=80, pump_on_time_s=0.2,
                             run_second_pump=True, second_pump_speed_pct=30)

    (args, kwargs), = calls
    assert args == (0.2,)
    assert kwargs == {"fill": True, "empty": True, "fill_speed_pct": 30, "empty_speed_pct": 80}


@pytest.mark.asyncio
async def test_how_often_acts_on_the_first_pass_and_every_nth(monkeypatch):
    bravo = _sim_bravo()
    passes = []

    async def counting_pump_reagent(**kwargs):
        passes.append(kwargs["location"])
        return {"status": "done"}

    monkeypatch.setattr(bravo, "pump_reagent", counting_pump_reagent)
    await _run(bravo, _loop(5, _fill(how_often=2)))
    assert len(passes) == 3  # passes 1, 3 and 5


@pytest.mark.asyncio
async def test_concurrent_pumping_is_stopped_when_the_workflow_ends():
    bravo = _sim_bravo()
    await _run(bravo, _chain(_fill(pump_on_time_s=60, allow_concurrent=True)))
    assert not _driver(bravo).is_running


@pytest.mark.asyncio
async def test_stop_pumps_step():
    bravo = _sim_bravo()
    bravo.run_autofill_pumps("autofill", duration_s=60)
    await bravo.autofill_stop_pumps(STATION)
    assert not _driver(bravo).is_running


@pytest.mark.asyncio
async def test_no_station_at_the_location_is_an_error():
    bravo = _sim_bravo()
    with pytest.raises(ValueError, match="location 5"):
        await bravo.pump_reagent(5)


def test_aborting_a_workflow_stops_running_pumps():
    bravo = _sim_bravo()
    bravo.run_autofill_pumps("autofill", duration_s=60)
    executor = WorkflowExecutor(bravo, _chain(), preview_animation=False)
    executor.abort()
    assert not _driver(bravo).is_running

"""The filament walkthrough against the fake printer: every step, the answers, cancel, Buddy's extras."""

import time

import pytest

from printpi_daemon.filament import DEFAULT_MOVES, FilamentError, FilamentRunner, FilamentState, buddy_filament_gcode, moves_duration
from printpi_daemon.printer import Printer

FAST = "fake://?time_scale=0.01"
NEXTRUDER = {
    "load": [[30, 360], [50, 1500]],
    "purge": [27, 180],
    "unload": [[8, 995], [-43, 6000], [-105, 1500]],
}


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def open_printer(url: str = FAST) -> Printer:
    p = Printer(url, connect_timeout=1.0, ok_timeout=5.0, temperature_interval=0.05)
    p.connect()
    return p


@pytest.fixture
def printer():
    p = open_printer()
    yield p
    if p._port is not None:
        p.disconnect()


@pytest.fixture
def seen() -> list[FilamentState]:
    return []


@pytest.fixture
def records() -> list[tuple[str, dict | None]]:
    return []


@pytest.fixture
def runner(printer, seen, records) -> FilamentRunner:
    return FilamentRunner(lambda: printer, on_state=seen.append, on_record=lambda event, spool: records.append((event, spool)))


def fake_of(printer: Printer):
    return printer._port


def at_step(runner: FilamentRunner, step: str, timeout: float = 10.0) -> FilamentState:
    assert wait_for(lambda: (runner.state or FilamentState("load")).step == step, timeout), f"never reached {step}: {runner.state}"
    return runner.state


def extrusions(printer: Printer) -> list[str]:
    return [command for command in fake_of(printer).commands if command.startswith("G1 E")]


# ---- pure helpers ---------------------------------------------------------------------


def test_buddy_presets_are_selected_by_name_and_tpu_is_flex():
    assert buddy_filament_gcode("PLA", 215) == 'M865 S"PLA" L0'
    assert buddy_filament_gcode("petg", 230) == 'M865 S"PETG" L0'
    assert buddy_filament_gcode("TPU", 230) == 'M865 S"FLEX" L0'


def test_buddy_custom_materials_get_a_seven_character_name_and_their_temperature():
    assert buddy_filament_gcode("PETG-CF", 250) == 'M865 X R N"PETG-CF" T250 P170 L0'
    assert buddy_filament_gcode("PLA Silk Rainbow", 220) == 'M865 X R N"PLA-SIL" T220 P170 L0'
    assert buddy_filament_gcode(None, None) == 'M865 X R N"CUSTOM" T215 P170 L0'


def test_moves_duration_sums_the_time_of_every_move():
    assert moves_duration([[30, 360], [50, 1500]]) == pytest.approx(5 + 2)
    assert moves_duration([[-105, 1500]]) == pytest.approx(4.2)


# ---- the walkthrough ------------------------------------------------------------------


def test_load_walks_through_every_step_and_records_the_spool(runner, printer, seen, records):
    state = runner.start("load", spool={"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"},
                         nozzle=215, moves=NEXTRUDER)
    assert state.action == "load"
    assert state.steps == ("heating", "insert", "loading", "purging", "check", "done")
    assert state.spool == {"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"}
    assert state.material == "PLA"

    insert = at_step(runner, "insert")
    assert insert.waiting
    assert fake_of(printer).hotend.target == 215
    assert "M104 S215" in fake_of(printer).commands
    runner.proceed()

    check = at_step(runner, "check")
    assert check.waiting
    assert check.purges == 1
    assert extrusions(printer) == ["G1 E30 F360", "G1 E50 F1500", "G1 E27 F180"]
    assert "M400" in fake_of(printer).commands
    runner.answer("yes")

    done = at_step(runner, "done")
    assert not done.active
    assert not done.waiting
    assert done.error is None
    assert done.finished_at is not None
    assert fake_of(printer).hotend.target == 0
    assert records == [("loaded", {"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"})]
    assert [s.step for s in seen if s.step == "heating"], "heating was published"
    assert "M865" not in " ".join(fake_of(printer).commands), "plain Marlin gets no Buddy filament type"


def test_purge_more_pushes_another_purge_length_before_asking_again(runner, printer):
    runner.start("load", material="PETG", nozzle=230, moves=NEXTRUDER)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")
    runner.answer("purge")
    assert wait_for(lambda: runner.state.purges == 2 and runner.state.step == "check")
    assert extrusions(printer).count("G1 E27 F180") == 2
    runner.answer("yes")
    at_step(runner, "done")


def test_unload_heats_rams_pulls_and_waits_for_the_filament_to_be_taken_out(runner, printer, records):
    runner.start("unload", material="PLA", unload_nozzle=215, moves=NEXTRUDER)
    remove = at_step(runner, "remove")
    assert remove.waiting
    assert remove.steps == ("heating", "unloading", "remove", "done")
    assert extrusions(printer) == ["G1 E8 F995", "G1 E-43 F6000", "G1 E-105 F1500"]
    assert fake_of(printer).hotend.target == 0, "the heater is off while the user pulls the filament"
    assert records == [("unloaded", None)]
    runner.proceed()
    at_step(runner, "done")


def test_change_unloads_the_old_filament_hot_enough_for_it_then_loads_the_new_one(runner, printer, records):
    runner.start("change", spool={"id": 7, "name": "Orange", "material": "PLA", "color": "#f26a2a"},
                 nozzle=215, unload_nozzle=260, moves=NEXTRUDER)
    remove = at_step(runner, "remove")
    assert remove.step_index == 2
    assert fake_of(printer).hotend.target == 260, "an unload heats to the old filament's temperature"
    assert records == [("unloaded", None)]
    runner.proceed()
    insert = at_step(runner, "insert")
    assert insert.step_index == 4, "the second heating counts on from the remove step"
    assert fake_of(printer).hotend.target == 215
    runner.proceed()
    at_step(runner, "check")
    runner.answer("yes")
    done = at_step(runner, "done")
    assert done.steps == ("heating", "unloading", "remove", "heating", "insert", "loading", "purging", "check", "done")
    assert done.step_index == 8
    assert records[-1] == ("loaded", {"id": 7, "name": "Orange", "material": "PLA", "color": "#f26a2a"})


def test_motion_steps_carry_a_duration_and_progress_by_time(runner, seen, printer):
    runner.start("load", material="PLA", nozzle=215, moves=NEXTRUDER)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")
    loading = [s for s in seen if s.step == "loading"]
    purging = [s for s in seen if s.step == "purging"]
    assert loading and loading[0].step_duration == pytest.approx(7)
    assert purging and purging[0].step_duration == pytest.approx(9)
    assert loading[0].progress == pytest.approx(0.0, abs=0.01)
    # The progress is read off the clock: half the duration in, half done.
    runner._step_began = time.monotonic() - 4.5
    runner._state.step_duration = 9.0
    runner._state.step = "purging"
    assert runner.state.progress == pytest.approx(0.5, abs=0.05)
    runner._state.step = "check"
    runner.answer("yes")
    at_step(runner, "done")


def test_cancel_turns_the_heater_off_and_ends_the_walkthrough(runner, printer, records):
    runner.start("load", material="PLA", nozzle=215, moves=NEXTRUDER)
    at_step(runner, "insert")
    runner.cancel()
    cancelled = at_step(runner, "cancelled")
    assert not cancelled.active
    assert cancelled.step_index == 1, "a cancel stays at the step it happened on"
    assert fake_of(printer).hotend.target == 0
    assert records == []
    with pytest.raises(FilamentError):
        runner.cancel()


def test_cancel_during_heating_is_prompt(runner, printer):
    runner.start("load", material="PLA", nozzle=215, moves=NEXTRUDER)
    assert wait_for(lambda: runner.state.step == "heating")
    started = time.monotonic()
    runner.cancel()
    at_step(runner, "cancelled")
    assert time.monotonic() - started < 3


def test_answers_and_continue_are_refused_at_the_wrong_step(runner, printer):
    with pytest.raises(FilamentError):
        runner.proceed()
    runner.start("load", material="PLA", nozzle=215, moves=NEXTRUDER)
    with pytest.raises(FilamentError):
        runner.answer("yes")
    at_step(runner, "insert")
    with pytest.raises(FilamentError):
        runner.answer("yes")
    with pytest.raises(FilamentError):
        runner.answer("maybe")
    with pytest.raises(FilamentError, match="already running"):
        runner.start("unload", unload_nozzle=215)
    runner.cancel()
    at_step(runner, "cancelled")


def test_start_refuses_bad_input(runner, printer):
    with pytest.raises(FilamentError, match="unknown filament action"):
        runner.start("wash")
    with pytest.raises(FilamentError, match="no temperature"):
        runner.start("load", material="PLA")
    printer.disconnect()
    with pytest.raises(FilamentError, match="not connected"):
        runner.start("unload", unload_nozzle=215)


def test_default_moves_serve_a_profile_without_any(runner, printer):
    runner.start("load", material="PLA", nozzle=215)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")
    expected = [f"G1 E{mm:g} F{feed:g}" for mm, feed in DEFAULT_MOVES["load"]] + [f"G1 E{DEFAULT_MOVES['purge'][0]:g} F{DEFAULT_MOVES['purge'][1]:g}"]
    assert extrusions(printer) == expected
    runner.answer("yes")
    at_step(runner, "done")


def test_extrusion_is_relative_for_the_moves_and_absolute_again_afterwards(runner, printer):
    runner.start("unload", unload_nozzle=215, moves=NEXTRUDER)
    at_step(runner, "remove")
    commands = fake_of(printer).commands
    assert commands.index("M83") < commands.index("G1 E8 F995") < commands.index("M400") < commands.index("M82")
    runner.proceed()
    at_step(runner, "done")


def test_buddy_gets_the_stall_detection_off_and_its_filament_type_set(seen, records):
    printer = open_printer("fake://?time_scale=0.01&firmware=buddy")
    try:
        runner = FilamentRunner(lambda: printer, on_state=seen.append)
        runner.start("load", material="PETG-CF", nozzle=250, moves=NEXTRUDER)
        at_step(runner, "insert")
        commands = fake_of(printer).commands
        assert "M591 S0" in commands
        runner.proceed()
        at_step(runner, "check")
        runner.answer("yes")
        at_step(runner, "done")
        commands = fake_of(printer).commands
        assert 'M865 X R N"PETG-CF" T250 P170 L0' in commands
        assert commands.index("M591 R") > commands.index('M865 X R N"PETG-CF" T250 P170 L0')
    finally:
        printer.disconnect()


def test_a_lost_connection_ends_the_walkthrough_with_an_error(runner, printer):
    runner.start("load", material="PLA", nozzle=215, moves=NEXTRUDER)
    at_step(runner, "insert")
    printer.disconnect()
    runner.proceed()
    error = at_step(runner, "error")
    assert error.error
    assert not error.active

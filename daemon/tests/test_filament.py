"""The filament walkthrough against the fake printer: every step, the answers, cancel, Buddy's extras."""

import time
import threading

import pytest

from printpi_daemon.filament import DEFAULT_MOVES, FilamentError, FilamentRunner, FilamentState, buddy_load_commands, moves_duration
from printpi_daemon.printer import Printer

FAST = "fake://?time_scale=0.01"
TEST_MOVES = {
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
    assert buddy_load_commands("PLA", 215) == ['M701 W2 S"PLA"']
    assert buddy_load_commands("petg", 230) == ['M701 W2 S"PETG"']
    assert buddy_load_commands("TPU", 230) == ['M701 W2 S"FLEX"']


def test_buddy_custom_materials_get_a_seven_character_name_and_their_temperature():
    assert buddy_load_commands("PETG-CF", 250) == ['M865 X R N"PETG-CF" T250 P170', 'M701 W2 S"#"']
    assert buddy_load_commands("PLA Silk Rainbow", 220) == ['M865 X R N"PLA-SIL" T220 P170', 'M701 W2 S"#"']
    assert buddy_load_commands(None, None) == ['M865 X R N"CUSTOM" T215 P170', 'M701 W2 S"#"']


def test_moves_duration_sums_the_time_of_every_move():
    assert moves_duration([[30, 360], [50, 1500]]) == pytest.approx(5 + 2)
    assert moves_duration([[-105, 1500]]) == pytest.approx(4.2)


# ---- the walkthrough ------------------------------------------------------------------


def test_load_walks_through_every_step_and_records_the_spool(runner, printer, seen, records):
    state = runner.start("load", spool={"id": 3, "name": "Galaxy Black", "material": "PLA", "color": "#26262e"},
                         nozzle=215, moves=TEST_MOVES)
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
    runner.start("load", material="PETG", nozzle=230, moves=TEST_MOVES)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")
    runner.answer("purge")
    assert wait_for(lambda: runner.state.purges == 2 and runner.state.step == "check")
    assert extrusions(printer).count("G1 E27 F180") == 2
    runner.answer("yes")
    at_step(runner, "done")


def test_unload_heats_rams_pulls_and_waits_for_the_filament_to_be_taken_out(runner, printer, records):
    runner.start("unload", material="PLA", unload_nozzle=215, moves=TEST_MOVES)
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
                 nozzle=215, unload_nozzle=260, moves=TEST_MOVES)
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
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
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
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
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
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
    assert wait_for(lambda: runner.state.step == "heating")
    started = time.monotonic()
    runner.cancel()
    at_step(runner, "cancelled")
    assert time.monotonic() - started < 3


def test_answers_and_continue_are_refused_at_the_wrong_step(runner, printer):
    with pytest.raises(FilamentError):
        runner.proceed()
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
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
    runner.start("unload", unload_nozzle=215, moves=TEST_MOVES)
    at_step(runner, "remove")
    commands = fake_of(printer).commands
    assert commands.index("M83") < commands.index("G1 E8 F995") < commands.index("M400") < commands.index("M82")
    runner.proceed()
    at_step(runner, "done")


def test_a_lost_connection_ends_the_walkthrough_with_an_error(runner, printer):
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
    at_step(runner, "insert")
    printer.disconnect()
    error = at_step(runner, "error")
    assert error.error
    assert not error.active


def test_purge_reheats_after_the_heater_times_out_during_the_colour_check(runner, printer):
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")
    fake = fake_of(printer)
    fake.hotend.set_target(0)
    fake.hotend.actual = 25
    printer.send("M105")
    before = len(fake.commands)

    runner.answer("purge")

    heating = at_step(runner, "heating")
    assert heating.step_index == 0
    assert wait_for(lambda: runner.state.step == "check" and runner.state.purges == 2)
    commands = fake.commands[before:]
    assert commands.index("M104 S215") < commands.index("G1 E27 F180")
    runner.answer("yes")
    at_step(runner, "done")


def test_a_lost_connection_during_the_colour_check_does_not_wait_for_an_answer(runner, printer):
    runner.start("load", material="PLA", nozzle=215, moves=TEST_MOVES)
    at_step(runner, "insert")
    runner.proceed()
    at_step(runner, "check")

    printer.disconnect()

    assert at_step(runner, "error").error == "printer disconnected during the colour check"


def test_repeating_purge_keeps_the_second_heat_up_of_a_change():
    state = FilamentState("change", steps=("heating", "unloading", "remove", "heating", "insert", "loading", "purging", "check", "done"), step_index=7)
    assert FilamentRunner._index_of(state, "heating") == 3
    assert FilamentRunner._index_of(state, "purging") == 6


@pytest.fixture
def native(monkeypatch, records, seen):
    """A stock-style blocking dialog: busy keepalives, then ok on success OR abort.

    Tests close the dialog explicitly, independently of PrintPi's result check.
    Use the actual Printer transport so disconnects and keepalives are exercised.
    """
    printer = open_printer("fake://?time_scale=0.01&firmware=buddy")
    fake = fake_of(printer)
    dialog_done = threading.Event()

    def dialog(params):
        while not dialog_done.wait(0.025):
            if fake._closed:
                return
            fake._emit("echo:busy: paused for user")
        dialog_done.clear()
        # Firmware alone chooses the final temperature; the runner must preserve it.
        fake.hotend.set_target(170 if fake._command.startswith("M701") else 0)
        fake._emit("ok")

    monkeypatch.setattr(fake, "_cmd_M701", dialog, raising=False)
    monkeypatch.setattr(fake, "_cmd_M702", dialog, raising=False)
    runner = FilamentRunner(lambda: printer, on_state=seen.append, on_record=lambda event, spool: records.append((event, spool)))
    yield runner, printer, fake, dialog_done
    printer.disconnect()
    runner.stop()


def test_native_load_waits_for_the_printer_and_only_records_a_confirmed_result(native, records):
    runner, printer, fake, dialog_done = native
    state = runner.start("load", spool={"id": 3, "material": "PLA"}, nozzle=215, moves=TEST_MOVES)
    assert state.backend == "firmware"
    assert state.steps == ("printer_load", "confirm_loaded", "done")
    assert wait_for(lambda: 'M701 W2 S"PLA"' in fake.commands)
    printer.ok_timeout = 0.1
    time.sleep(0.3)  # busy keepalives keep a display question alive beyond the timeout
    assert runner.state.step == "printer_load"
    assert runner.state.progress is None
    assert runner.state.step_duration is None
    assert not runner.state.waiting
    assert records == []
    with pytest.raises(FilamentError, match="printer display"):
        runner.cancel()
    with pytest.raises(FilamentError):
        runner.proceed()
    with pytest.raises(FilamentError):
        runner.answer("yes")

    dialog_done.set()
    assert at_step(runner, "confirm_loaded").waiting
    assert records == []
    runner.proceed()
    at_step(runner, "done")
    assert records == [("loaded", {"id": 3, "name": "", "material": "PLA", "color": None})]
    assert fake.hotend.target == 170
    assert not any(command.startswith(("G", "M83", "M82", "M104", "M591", "M865")) for command in fake.commands)


def test_native_custom_material_is_prepared_without_claiming_it_is_loaded(native, records):
    runner, printer, fake, dialog_done = native
    runner.start("load", material="PETG-CF", nozzle=250)
    assert wait_for(lambda: 'M701 W2 S"#"' in fake.commands)
    assert fake.commands.index('M865 X R N"PETG-CF" T250 P170') < fake.commands.index('M701 W2 S"#"')
    assert not any("L0" in command for command in fake.commands)
    dialog_done.set()
    at_step(runner, "confirm_loaded")
    runner.proceed()
    at_step(runner, "done")
    assert records == [("loaded", None)]


def test_native_unload_finishes_after_confirmed_removal(native, records):
    runner, printer, fake, dialog_done = native
    runner.start("unload", unload_nozzle=260)
    assert wait_for(lambda: "M702 W2" in fake.commands)
    dialog_done.set()
    at_step(runner, "confirm_unloaded")
    runner.proceed()
    at_step(runner, "done")
    assert records == [("unloaded", None)]
    assert not any(command.startswith(("M701", "M104", "G1")) for command in fake.commands)


def test_native_change_waits_for_removal_before_loading_and_books_both_outcomes(native, records):
    runner, printer, fake, dialog_done = native
    runner.start("change", material="PLA", nozzle=215, unload_nozzle=260)
    assert wait_for(lambda: "M702 W2" in fake.commands)
    assert not any(command.startswith("M701") for command in fake.commands)
    dialog_done.set()
    assert at_step(runner, "confirm_unloaded").step_index == 1
    assert records == []
    assert not any(command.startswith("M701") for command in fake.commands)
    runner.proceed()
    assert wait_for(lambda: 'M701 W2 S"PLA"' in fake.commands)
    assert records == [("unloaded", None)]
    dialog_done.set()
    assert at_step(runner, "confirm_loaded").step_index == 3
    runner.proceed()
    assert at_step(runner, "done").step_index == 4
    assert records == [("unloaded", None), ("loaded", None)]
    assert extrusions(printer) == []


@pytest.mark.parametrize("action, confirmation", [("load", "confirm_loaded"), ("unload", "confirm_unloaded"), ("change", "confirm_unloaded")])
def test_aborting_a_native_dialog_never_books_filament_or_continues_the_change(native, records, action, confirmation):
    runner, printer, fake, dialog_done = native
    runner.start(action, material="PLA", nozzle=215)
    assert wait_for(lambda: any(command.startswith(("M701", "M702")) for command in fake.commands))
    dialog_done.set()  # Stop on the printer also returns ok.
    at_step(runner, confirmation)
    runner.cancel()
    at_step(runner, "cancelled")
    assert records == []
    if action == "change":
        assert not any(command.startswith("M701") for command in fake.commands)
    assert "M104 S0" not in fake.commands


def test_cancel_after_confirmed_unload_keeps_the_inventory_empty(native, records):
    runner, printer, fake, dialog_done = native
    runner.start("change", material="PLA", nozzle=215)
    dialog_done.set()
    at_step(runner, "confirm_unloaded")
    runner.proceed()
    assert wait_for(lambda: 'M701 W2 S"PLA"' in fake.commands)
    dialog_done.set()
    at_step(runner, "confirm_loaded")
    runner.cancel()
    at_step(runner, "cancelled")
    assert records == [("unloaded", None)]


@pytest.mark.parametrize("reply, material", [('echo:Unknown command: "M701"', 'PLA'), ('Error:Invalid filament name', 'PETG-CF')])
def test_rejected_native_commands_fail_without_falling_back_to_extrusion(native, monkeypatch, records, reply, material):
    runner, printer, fake, dialog_done = native
    def reject(params):
        fake._emit(reply)
        fake._emit("ok")
    monkeypatch.setattr(fake, "_cmd_M701" if material == "PLA" else "_cmd_M865", reject, raising=False)
    runner.start("load", material=material, nozzle=250)
    assert "Printer rejected" in at_step(runner, "error").error
    assert records == []
    assert extrusions(printer) == []
    if material == "PETG-CF":
        assert not any(command.startswith("M701") for command in fake.commands)


def test_material_parameter_output_is_not_mistaken_for_a_command_error(native, monkeypatch):
    runner, printer, fake, dialog_done = native

    def parameters(params):
        fake._emit("name:INVALID")
        fake._emit("nozzle_temperature:215")
        fake._emit("ok")

    monkeypatch.setattr(fake, "_cmd_M865", parameters, raising=False)
    runner.start("load", material="INVALID", nozzle=215)
    assert wait_for(lambda: 'M701 W2 S"#"' in fake.commands)
    dialog_done.set()
    at_step(runner, "confirm_loaded")
    runner.proceed()
    at_step(runner, "done")


def test_shutdown_during_a_native_dialog_never_advances_or_records_its_result(native, records):
    runner, printer, fake, dialog_done = native
    runner.start("change", material="PLA", nozzle=215)
    assert wait_for(lambda: "M702 W2" in fake.commands)
    shutdown = threading.Thread(target=runner.stop)
    shutdown.start()
    try:
        assert wait_for(lambda: runner._cancelled)
        dialog_done.set()
        at_step(runner, "cancelled")
        assert records == []
        assert not any(command.startswith("M701") for command in fake.commands)
    finally:
        dialog_done.set()
        shutdown.join(timeout=1)


@pytest.mark.parametrize("close_dialog", [False, True])
def test_native_disconnect_fails_during_the_dialog_or_result_confirmation(native, records, close_dialog):
    runner, printer, fake, dialog_done = native
    runner.start("load", material="PLA", nozzle=215)
    assert wait_for(lambda: 'M701 W2 S"PLA"' in fake.commands)
    if close_dialog:
        dialog_done.set()
        at_step(runner, "confirm_loaded")
    printer.disconnect()
    assert at_step(runner, "error").error
    assert records == []

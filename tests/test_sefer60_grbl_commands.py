"""
ספר 60 – full GRBL command trace test.

Runs the complete rows operation for program 'ספר 60' and prints every GRBL
command that would be sent to the machine, in execution order, with:
  - step index
  - commanded position (cm)
  - GRBL command string  (G0/G1 X{mm} Y{mm})
  - anti-backlash overshoot when direction reverses
  - distance of each mark from the paper edge

Every command is also asserted to match the expected value derived directly
from the program parameters and paper_start_x so we can see if anything drifts.
"""

import sys, os, json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.csv_parser import CSVParser
import core.step_generator as sg


# ── Load settings & program ──────────────────────────────────────────────────

with open('config/settings.json') as f:
    _settings = json.load(f)

PAPER_X   = _settings['hardware_limits']['paper_start_x']   # cm
PAPER_Y   = _settings['hardware_limits']['paper_start_y']   # cm
FEED_RATE = _settings['hardware_config']['arduino_grbl']['grbl_settings']['feed_rate']  # mm/min
AB_ENABLED= _settings['hardware_config']['arduino_grbl'].get('anti_backlash_enabled', False)
AB_X_CM   = _settings['hardware_config']['arduino_grbl'].get('backlash_compensation_x_cm', 0.0)

_programs, _errors = CSVParser().load_programs_from_csv('data/sample_programs.csv')
SEFER60 = next(p for p in _programs if 'ספר 60' in p.program_name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def cm_to_grbl_mm(cm: float) -> float:
    """Convert cm to GRBL mm (× 10).  This is the ONLY conversion in arduino_grbl.py."""
    return round(cm * 10.0, 3)


def grbl_g1(x_cm: float, y_cm: float) -> str:
    return f"G1 X{cm_to_grbl_mm(x_cm):.3f} Y{cm_to_grbl_mm(y_cm):.3f} F{FEED_RATE}"


def grbl_g0(x_cm: float, y_cm: float) -> str:
    return f"G0 X{cm_to_grbl_mm(x_cm):.3f} Y{cm_to_grbl_mm(y_cm):.3f}"


def simulate_grbl_commands(steps, paper_x, ab_enabled, ab_x_cm, feed_rate):
    """
    Walk through every step and produce the list of GRBL commands that
    arduino_grbl.py would actually send, in order.

    Returns a list of dicts with keys:
        step_idx, step_op, description,
        cmd_type,           # 'G0' | 'G1' | 'TOOL' | 'SENSOR' | 'WAIT'
        commanded_x_cm,     # None for non-move steps
        grbl_command,       # full GRBL string or action label
        is_overshoot,       # True only for anti-backlash G0 move
        dist_from_paper_cm  # commanded_x_cm - paper_x  (None for non-move)
    """
    current_x = 0.0   # work coord origin after homing + G10
    current_y = 0.0   # Y stays at 0 during rows
    last_x_dir = 0    # +1 right, -1 left, 0 initial

    records = []

    for idx, step in enumerate(steps):
        op   = step.get('operation', '')
        desc = step.get('description', '')
        params = step.get('parameters', {})

        if op == 'move_x':
            target_x = params['position']
            new_dir = (1 if target_x > current_x else -1 if target_x < current_x else 0)
            reversed_dir = (last_x_dir != 0 and new_dir != 0 and new_dir != last_x_dir)

            # ── anti-backlash overshoot ──────────────────────────────────────
            if ab_enabled and reversed_dir:
                ov_x = target_x - new_dir * ab_x_cm   # opposite-direction overshoot
                records.append(dict(
                    step_idx=idx,
                    step_op='move_x [AB overshoot]',
                    description=f'  ↳ anti-backlash overshoot before: {desc[:60]}',
                    cmd_type='G0',
                    commanded_x_cm=ov_x,
                    grbl_command=grbl_g0(ov_x, current_y),
                    is_overshoot=True,
                    dist_from_paper_cm=round(ov_x - paper_x, 4),
                ))
                last_x_dir = -new_dir  # overshoot goes opposite to new_dir

            # ── main move ────────────────────────────────────────────────────
            records.append(dict(
                step_idx=idx,
                step_op='move_x',
                description=desc,
                cmd_type='G1',
                commanded_x_cm=target_x,
                grbl_command=grbl_g1(target_x, current_y),
                is_overshoot=False,
                dist_from_paper_cm=round(target_x - paper_x, 4),
            ))
            if new_dir != 0:
                last_x_dir = new_dir
            current_x = target_x

        elif op == 'move_y':
            target_y = params['position']
            records.append(dict(
                step_idx=idx,
                step_op='move_y',
                description=desc,
                cmd_type='G1',
                commanded_x_cm=None,
                grbl_command=grbl_g1(current_x, target_y),
                is_overshoot=False,
                dist_from_paper_cm=None,
            ))
            current_y = target_y

        elif op == 'tool_action':
            tool   = params.get('tool', '?')
            action = params.get('action', '?')
            records.append(dict(
                step_idx=idx,
                step_op='tool_action',
                description=desc,
                cmd_type='TOOL',
                commanded_x_cm=None,
                grbl_command=f'{tool} → {action}',
                is_overshoot=False,
                dist_from_paper_cm=None,
            ))

        elif op == 'wait_sensor':
            sensor = params.get('sensor', '?')
            records.append(dict(
                step_idx=idx,
                step_op='wait_sensor',
                description=desc,
                cmd_type='SENSOR',
                commanded_x_cm=None,
                grbl_command=f'wait sensor: {sensor}',
                is_overshoot=False,
                dist_from_paper_cm=None,
            ))

        else:
            records.append(dict(
                step_idx=idx, step_op=op, description=desc,
                cmd_type='OTHER', commanded_x_cm=None,
                grbl_command=op, is_overshoot=False, dist_from_paper_cm=None,
            ))

    return records


# ── Build full trace once ─────────────────────────────────────────────────────

def _build_trace():
    steps = sg.generate_row_marking_steps(SEFER60)
    return simulate_grbl_commands(steps, PAPER_X, AB_ENABLED, AB_X_CM, FEED_RATE)

_TRACE = _build_trace()
_MOVE_X = [r for r in _TRACE if r['step_op'] in ('move_x', 'move_x [AB overshoot]')]


# ── Print the full trace (always runs when pytest -s is used) ─────────────────

def _print_trace():
    p = SEFER60
    print()
    print("=" * 80)
    print("ספר 60 — FULL GRBL COMMAND TRACE")
    print("=" * 80)
    print(f"  paper_start_x     = {PAPER_X} cm  →  GRBL X{cm_to_grbl_mm(PAPER_X):.1f} mm")
    print(f"  paper_start_y     = {PAPER_Y} cm  →  GRBL Y{cm_to_grbl_mm(PAPER_Y):.1f} mm")
    print(f"  program width     = {p.width} cm")
    print(f"  dm_left           = {p.rows_double_margin_left} cm  (distance from paper left → double mark)")
    print(f"  left_margin       = {p.left_margin} cm  (distance from double mark → page edge)")
    print(f"  page_width        = {p.page_width} cm  ×  {p.number_of_pages} pages")
    print(f"  buffer            = {p.buffer_between_pages} cm  between pages")
    print(f"  dm_right          = {p.rows_double_margin_right} cm  (distance from double mark → paper right)")
    print(f"  right_margin      = {p.right_margin} cm")
    print(f"  anti-backlash     = {AB_ENABLED}  ({AB_X_CM} cm)")
    print(f"  feed_rate         = {FEED_RATE} mm/min")
    print()
    print(f"  Expected X positions (cm):                  GRBL mm:")
    print(f"    left  cut   = {PAPER_X:.3f} cm               X{cm_to_grbl_mm(PAPER_X):.1f}")
    dbl_l = PAPER_X + p.rows_double_margin_left
    print(f"    double left = {dbl_l:.3f} cm               X{cm_to_grbl_mm(dbl_l):.1f}")
    pg0_l = PAPER_X + p.rows_double_margin_left + p.left_margin
    print(f"    page 0 left = {pg0_l:.3f} cm               X{cm_to_grbl_mm(pg0_l):.1f}")
    dbl_r = PAPER_X + p.width - p.rows_double_margin_right
    print(f"    double right= {dbl_r:.3f} cm               X{cm_to_grbl_mm(dbl_r):.1f}")
    right_cut = PAPER_X + p.width * p.repeat_rows
    print(f"    right cut   = {right_cut:.3f} cm               X{cm_to_grbl_mm(right_cut):.1f}")
    print()

    # Full command table
    print(f"{'#':>4}  {'TYPE':<22}  {'GRBL COMMAND':<40}  {'dist from paper':>17}  DESCRIPTION")
    print("-" * 120)
    for r in _TRACE:
        dist = f"{r['dist_from_paper_cm']:+.3f} cm" if r['dist_from_paper_cm'] is not None else ""
        marker = " ◄ OVERSHOOT" if r['is_overshoot'] else ""
        print(
            f"{r['step_idx']:>4}  {r['step_op']:<22}  {r['grbl_command']:<40}  "
            f"{dist:>17}  {r['description'][:55]}{marker}"
        )
    print("=" * 80)
    print()


_print_trace()


# ── Assertions ────────────────────────────────────────────────────────────────

class TestSefer60GRBLCommands:
    """Assert every GRBL command is exactly correct for ספר 60."""

    p = SEFER60

    # ── cm→mm conversion ──────────────────────────────────────────────────────

    def test_grbl_conversion_is_cm_times_10(self):
        """Every move_x position: GRBL mm == commanded_cm × 10 (no other multiplier)."""
        for r in _MOVE_X:
            expected_mm = r['commanded_x_cm'] * 10.0
            actual_mm = float(r['grbl_command'].split('X')[1].split()[0])
            assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
                f"step {r['step_idx']}: commanded {r['commanded_x_cm']}cm → "
                f"GRBL X{actual_mm}mm but expected X{expected_mm}mm"
            )

    # ── paper cuts ────────────────────────────────────────────────────────────

    def test_right_cut_grbl_command(self):
        """Right paper cut: G1 X{(paper_x+width)*10} — first move in sequence."""
        r = next(r for r in _TRACE if 'right paper edge' in r['description'].lower()
                 and r['cmd_type'] == 'G1')
        expected_x_cm = PAPER_X + self.p.width * self.p.repeat_rows
        expected_mm = cm_to_grbl_mm(expected_x_cm)
        actual_mm = float(r['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"Right cut: G1 X{actual_mm} but expected X{expected_mm}"
        )

    def test_left_cut_grbl_command(self):
        """Left paper cut: G1 X{paper_x*10}."""
        r = next(r for r in _TRACE if 'left paper edge' in r['description'].lower()
                 and r['cmd_type'] == 'G1')
        expected_mm = cm_to_grbl_mm(PAPER_X)
        actual_mm = float(r['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"Left cut: G1 X{actual_mm} but expected X{expected_mm}"
        )

    # ── double margin marks ───────────────────────────────────────────────────

    def test_double_left_grbl_command(self):
        """double_left mark: G1 X{(paper_x + dm_left)*10}."""
        r = next(r for r in _TRACE if 'double margin left' in r['description'].lower()
                 and r['cmd_type'] == 'G1' and not r['is_overshoot'])
        expected_x_cm = PAPER_X + self.p.rows_double_margin_left
        expected_mm   = cm_to_grbl_mm(expected_x_cm)
        actual_mm     = float(r['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"double_left: G1 X{actual_mm}mm  expected X{expected_mm}mm\n"
            f"  = (paper_start_x={PAPER_X} + dm_left={self.p.rows_double_margin_left}) × 10"
        )

    def test_double_right_grbl_command(self):
        """double_right mark: G1 X{(paper_x + width - dm_right)*10}."""
        r = next(r for r in _TRACE if 'double margin right' in r['description'].lower()
                 and r['cmd_type'] == 'G1' and not r['is_overshoot'])
        expected_x_cm = PAPER_X + self.p.width - self.p.rows_double_margin_right
        expected_mm   = cm_to_grbl_mm(expected_x_cm)
        actual_mm     = float(r['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"double_right: G1 X{actual_mm}mm  expected X{expected_mm}mm\n"
            f"  = (paper_start_x={PAPER_X} + width={self.p.width} "
            f"- dm_right={self.p.rows_double_margin_right}) × 10"
        )

    # ── page edge marks ───────────────────────────────────────────────────────

    def test_page_0_left_edge_grbl_command(self):
        """Leftmost page left edge: G1 X{(paper_x + dm_left + left_margin)*10}."""
        p = self.p
        page_left_marks = [
            r for r in _TRACE
            if 'left edge' in r['description'].lower()
            and 'double' not in r['description'].lower()
            and 'cut' not in r['description'].lower()
            and r['cmd_type'] == 'G1'
        ]
        # page 0 is leftmost → smallest X
        leftmost = min(page_left_marks, key=lambda r: r['commanded_x_cm'])
        expected_x_cm = PAPER_X + p.rows_double_margin_left + p.left_margin
        expected_mm   = cm_to_grbl_mm(expected_x_cm)
        actual_mm     = float(leftmost['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"page-0 left edge: G1 X{actual_mm}mm  expected X{expected_mm}mm\n"
            f"  = (paper_x={PAPER_X} + dm_left={p.rows_double_margin_left} "
            f"+ left_margin={p.left_margin}) × 10"
        )

    def test_page_3_right_edge_grbl_command(self):
        """Rightmost page right edge: G1 X{(paper_x+dm_left+left_margin+(N-1)*(pw+buf)+pw)*10}."""
        p = self.p
        expected_x_cm = (
            PAPER_X + p.rows_double_margin_left + p.left_margin
            + (p.number_of_pages - 1) * (p.page_width + p.buffer_between_pages)
            + p.page_width
        )
        expected_mm = cm_to_grbl_mm(expected_x_cm)
        page_right_marks = [
            r for r in _TRACE
            if 'right edge' in r['description'].lower()
            and 'double' not in r['description'].lower()
            and 'cut' not in r['description'].lower()
            and r['cmd_type'] == 'G1'
        ]
        rightmost = max(page_right_marks, key=lambda r: r['commanded_x_cm'])
        actual_mm = float(rightmost['grbl_command'].split('X')[1].split()[0])
        assert actual_mm == pytest.approx(expected_mm, abs=0.001), (
            f"page-3 right edge: G1 X{actual_mm}mm  expected X{expected_mm}mm"
        )

    # ── distances from paper edge ─────────────────────────────────────────────

    def test_double_left_is_dm_left_cm_from_paper(self):
        """double_left GRBL position is exactly dm_left cm from paper left edge."""
        r = next(r for r in _TRACE if 'double margin left' in r['description'].lower()
                 and not r['is_overshoot'] and r['cmd_type'] == 'G1')
        assert r['dist_from_paper_cm'] == pytest.approx(self.p.rows_double_margin_left)

    def test_double_right_is_dm_right_cm_from_paper(self):
        """double_right GRBL position is exactly dm_right cm from paper right edge."""
        r = next(r for r in _TRACE if 'double margin right' in r['description'].lower()
                 and not r['is_overshoot'] and r['cmd_type'] == 'G1')
        right_cut_cm = PAPER_X + self.p.width * self.p.repeat_rows
        dist_from_right = right_cut_cm - r['commanded_x_cm']
        assert dist_from_right == pytest.approx(self.p.rows_double_margin_right)

    # ── anti-backlash ─────────────────────────────────────────────────────────

    def test_anti_backlash_overshoot_count(self):
        """Exactly one anti-backlash overshoot: when direction reverses after the right cut."""
        overshoots = [r for r in _TRACE if r['is_overshoot']]
        assert len(overshoots) == 1, (
            f"Expected 1 anti-backlash overshoot, got {len(overshoots)}"
        )

    def test_anti_backlash_overshoot_is_rightward(self):
        """The overshoot is to the RIGHT of the double_right target (x + backlash)."""
        ov = next(r for r in _TRACE if r['is_overshoot'])
        target_after = next(
            r for r in _TRACE[_TRACE.index(ov) + 1:]
            if r['cmd_type'] == 'G1' and r['commanded_x_cm'] is not None
        )
        assert ov['commanded_x_cm'] > target_after['commanded_x_cm'], (
            f"Overshoot {ov['commanded_x_cm']}cm should be > target {target_after['commanded_x_cm']}cm"
        )
        assert ov['commanded_x_cm'] == pytest.approx(
            target_after['commanded_x_cm'] + AB_X_CM, abs=0.001
        )

    def test_anti_backlash_final_target_unchanged(self):
        """After the overshoot G0, the G1 command goes to the original target, not the overshoot."""
        ov = next(r for r in _TRACE if r['is_overshoot'])
        final = next(
            r for r in _TRACE[_TRACE.index(ov) + 1:]
            if r['cmd_type'] == 'G1' and r['commanded_x_cm'] is not None
        )
        # final must be the double_right target
        expected_x_cm = PAPER_X + self.p.width - self.p.rows_double_margin_right
        assert final['commanded_x_cm'] == pytest.approx(expected_x_cm, abs=0.001)

    # ── Y stays at 0 during all X moves ──────────────────────────────────────

    def test_y_is_zero_in_all_move_x_commands(self):
        """Every move_x GRBL command has Y0.000 (Y stays at home during rows)."""
        for r in _MOVE_X:
            y_part = float(r['grbl_command'].split('Y')[1].split()[0].split('F')[0])
            assert y_part == pytest.approx(0.0), (
                f"step {r['step_idx']}: expected Y0.000 but got Y{y_part:.3f} "
                f"in command: {r['grbl_command']}"
            )

    # ── return to home ────────────────────────────────────────────────────────

    def test_final_command_returns_to_home(self):
        """Last move_x is G1 X0.000 Y0.000 (motor returns to home position)."""
        last_move = [r for r in _TRACE if r['step_op'] == 'move_x'][-1]
        assert last_move['commanded_x_cm'] == 0.0
        assert 'X0.000' in last_move['grbl_command']

    # ── full sequence order ───────────────────────────────────────────────────

    def test_sequence_starts_with_move_y_to_zero(self):
        """First step must be move_y to 0 (ensure lines motor at home)."""
        first = _TRACE[0]
        assert first['step_op'] == 'move_y'
        assert 'Y0.000' in first['grbl_command']

    def test_sequence_starts_with_right_cut_then_moves_left(self):
        """Execution order: right cut first, then moves left (RTL)."""
        move_x_cmds = [r for r in _TRACE if r['step_op'] == 'move_x']
        # First actual move_x is the right paper cut (largest X)
        first_x = move_x_cmds[0]['commanded_x_cm']
        # All subsequent non-overshoot moves should be ≤ first_x
        subsequent = [r for r in move_x_cmds[1:] if not r['is_overshoot']]
        for r in subsequent:
            assert r['commanded_x_cm'] <= first_x, (
                f"step {r['step_idx']} goes to {r['commanded_x_cm']}cm "
                f"which is right of first cut {first_x}cm — wrong direction!"
            )

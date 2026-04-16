from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3


def _default_header():
    return MachineHandler().g_code


def test_linear_move():
    h = _default_header()
    machine = MachineHandler()
    start_point = Vec3(0, 0, 0)
    end_point = Vec3(1, 1, 1)
    machine._linear_move(start_point, end_point)
    assert machine.g_code == h + "G1 X1.00000 Y1.00000 F2500 E0.00000\n"
    start_point = Vec3(3, 3, 3)
    end_point = Vec3(6, 6, 6)
    machine._linear_move(start_point, end_point)
    assert machine.g_code == h + (
        "G1 X1.00000 Y1.00000 F2500 E0.00000\n"
        "G1 X6.00000 Y6.00000 F2500 E0.00000\n"
    )


def test_arc_move():
    h = _default_header()
    machine = MachineHandler()
    start_point = Vec3(0, 0, 0)
    end_point = Vec3(1, 1, 1)
    machine._arc_move(start_point, end_point, 1, 1, "G2")
    assert machine.g_code == h + "G2 X1.00000 Y1.00000 I1.00000 J1.00000 F2500 E0.00000\n"
    start_point = end_point
    end_point = Vec3(2, 2, 2)
    machine._arc_move(start_point, end_point, 1, 1, "G3")
    assert machine.g_code == h + (
        "G2 X1.00000 Y1.00000 I1.00000 J1.00000 F2500 E0.00000\n"
        "G3 X2.00000 Y2.00000 I1.00000 J1.00000 F2500 E0.00000\n"
    )
    machine._arc_move(start_point, end_point, 1, 1, "G3")
    assert machine.g_code == h + (
        "G2 X1.00000 Y1.00000 I1.00000 J1.00000 F2500 E0.00000\n"
        "G3 X2.00000 Y2.00000 I1.00000 J1.00000 F2500 E0.00000\n"
        "G3 X2.00000 Y2.00000 I1.00000 J1.00000 F2500 E0.00000\n"
    )


def test_linear_move_extreme_values():
    h = _default_header()
    machine = MachineHandler()
    start_point = Vec3(-1000, -1000, 0)
    end_point = Vec3(1000, 1000, 0)
    machine._linear_move(start_point, end_point)
    assert machine.g_code == h + "G1 X1000.00000 Y1000.00000 F2500 E0.00000\n"


def test_arc_move_extreme_values():
    h = _default_header()
    machine = MachineHandler()
    start_point = Vec3(-1000, -1000, 0)
    end_point = Vec3(1000, 1000, 0)
    machine._arc_move(start_point, end_point, 500, 500, "G2")
    assert machine.g_code == h + (
        "G2 X1000.00000 Y1000.00000 I500.00000 J500.00000 F2500 E0.00000\n"
    )


def test_extrusion():
    h = _default_header()
    machine = MachineHandler(e=1.5)
    start_point = Vec3(0, 0, 0)
    end_point = Vec3(1, 1, 0)
    machine._linear_move(start_point, end_point)
    import math

    dist = math.sqrt(2)
    e_val = dist * 1.5 * 1.0
    assert machine.g_code == h + f"G1 X1.00000 Y1.00000 F2500 E{e_val:.5f}\n"

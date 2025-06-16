from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3

#Este test no consideran extruder por eso el espacio al final de G1,G2 y G3.
def test_linear_move():
    machine = MachineHandler()
    start_point = Vec3(0,0,0)
    end_point = Vec3(1,1,1)
    machine._linear_move(start_point,end_point)
    result = 'G1 X1.0 Y1.0 Z0 F2500 \n'
    assert machine.g_code == result
    start_point = Vec3(3,3,3)
    end_point = Vec3(6,6,6)
    machine._linear_move(start_point,end_point)
    result += "G0 X3.0 Y3.0 Z0.5 F2500\nG1 X6.0 Y6.0 Z0 F2500 \n"
    assert machine.g_code == result


#Este test no consideran extruder por eso el espacio al final de G1,G2 y G3.
def test_arc_move():
    machine = MachineHandler()
    start_point = Vec3(0,0,0)
    end_point = Vec3(1,1,1)
    machine._arc_move(start_point,end_point,1,1,2)
    result = 'G2 X1.0 Y1.0 Z0 I1 J1 F2500 \n'
    print(f'result = {result} gcode = {machine.g_code}')
    assert machine.g_code == result
    start_point = end_point
    end_point = Vec3(2,2,2)
    machine._arc_move(start_point,end_point,1,1,3)
    result += 'G3 X2.0 Y2.0 Z0 I1 J1 F2500 \n'
    print(f'result = {result} gcode = {machine.g_code}')
    assert machine.g_code == result 
    machine._arc_move(start_point,end_point,1,1,3)
    result += 'G0 X1.0 Y1.0 Z0.5 F2500\nG3 X2.0 Y2.0 Z0 I1 J1 F2500 \n'
    print(f'result = {result} gcode = {machine.g_code}')
    assert machine.g_code == result


#Este test no consideran extruder por eso el espacio al final de G1,G2 y G3.
def test_linear_move_extreme_values():
    machine = MachineHandler()
    start_point = Vec3(-1000, -1000, 0)
    end_point = Vec3(1000, 1000, 0)
    machine._linear_move(start_point, end_point)
    result = 'G0 X-1000.0 Y-1000.0 Z0.5 F2500\nG1 X1000.0 Y1000.0 Z0 F2500 \n'
    assert machine.g_code == result


#Este test no consideran extruder por eso el espacio al final de G1,G2 y G3.
def test_arc_move_extreme_values():
    machine = MachineHandler()
    start_point = Vec3(-1000, -1000, 0)
    end_point = Vec3(1000, 1000, 0)
    machine._arc_move(start_point, end_point, 500, 500, 2)
    result = 'G0 X-1000.0 Y-1000.0 Z0.5 F2500\nG2 X1000.0 Y1000.0 Z0 I500 J500 F2500 \n'
    assert machine.g_code == result

def test_extrusion():
    machine = MachineHandler(e=1.5)
    start_point = Vec3(0, 0, 0)
    end_point = Vec3(1, 1, 0)
    machine._linear_move(start_point, end_point)
    result = 'G1 X1.0 Y1.0 Z0 F2500 E1.5\n'
    assert machine.g_code == result
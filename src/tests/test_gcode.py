from src.core.gcode_generator import GcodeGenerator
from ezdxf.math import Vec3
import math as m
from src.core.gcode_generator import InvalidPointError


def compare_vec3(vec1, vec2, tol=1e-9):
    return m.isclose(vec1.x, vec2.x, abs_tol=tol) and m.isclose(vec1.y, vec2.y, abs_tol=tol) and m.isclose(vec1.z, vec2.z, abs_tol=tol)

def test_line_entity():
        gcode = GcodeGenerator()
        ps = Vec3(0,0,0)
        pe = Vec3(1.0,1.0,0)
        result = [{
            'command': 'G1',
            'param': {
                'start': ps,
                'end': pe,
                'layer': 'contorno',
                'id': 2
            }
        }]
        gcode.line_entity(ps,pe,'contorno',2)
        assert gcode.entity_list == result
        ps = Vec3(0,0,0)
        pe = Vec3(1000.0,155.0,0)
        result.append ({
            'command': 'G1',
            'param': {
                'start': ps,
                'end': pe,
                'layer': 'relleno',
                'id': 1
            }
        })
        gcode.line_entity(ps,pe,'relleno',1)
        assert gcode.entity_list == result


def test_arc_entity():
    #Principal problema cae en el redondeo a cero   
    gcode = GcodeGenerator()
    result = []
    center = Vec3(0,0,0)
    radius = 5
    alpha = 45.0
    beta = 90.0
    sp = Vec3((5*m.sqrt(2)/2),(5*m.sqrt(2)/2),0)
    ep = Vec3(0,5,0)
    result.append({
        'command': 'G2-3',
        'param': {
            'start': sp,
            'end': ep,
            'i': center.x - sp.x,
            'j': center.y - sp.y,
            'value': 3, #giramos de 45 a 90 ccw
            'layer': 'relleno',
            'id': 1
        }
    })
    gcode.arc_entity(center,radius,alpha,beta,'relleno',1)
    
    # Comparar cada parámetro con tolerancia
    generated = gcode.entity_list[0]
    expected = result[0]
    assert generated['command'] == expected['command']
    assert compare_vec3(generated['param']['start'], expected['param']['start'])
    assert compare_vec3(generated['param']['end'], expected['param']['end'])
    assert m.isclose(generated['param']['i'], expected['param']['i'], abs_tol=1e-9)
    assert m.isclose(generated['param']['j'], expected['param']['j'], abs_tol=1e-9)
    assert generated['param']['value'] == expected['param']['value']
    assert generated['param']['layer'] == expected['param']['layer']
    assert generated['param']['id'] == expected['param']['id']


def test_adjust_to_reference():
    gcode = GcodeGenerator()
    gcode.entity_list = [
        {'command': 'G1', 'param': {'start': Vec3(5, 5, 0), 'end': Vec3(10, 10, 0), 'layer': 'contorno', 'id': 1}},
        {'command': 'G1', 'param': {'start': Vec3(0, 0, 0), 'end': Vec3(5, 5, 0), 'layer': 'contorno', 'id': 2}}
    ]
    gcode.adjust_to_reference()
    expected = [
        {'command': 'G1', 'param': {'start': Vec3(5, 5, 0) - Vec3(0, 0, 0), 'end': Vec3(10, 10, 0) - Vec3(0, 0, 0), 'layer': 'contorno', 'id': 1}},
        {'command': 'G1', 'param': {'start': Vec3(0, 0, 0) - Vec3(0, 0, 0), 'end': Vec3(5, 5, 0) - Vec3(0, 0, 0), 'layer': 'contorno', 'id': 2}}
    ]
    assert gcode.entity_list == expected


def test_order_entity_list():
    gcode = GcodeGenerator()
    entity_list = [
        {'command': 'G1', 'param': {'start': Vec3(0, 0, 0), 'end': Vec3(1, 1, 0), 'layer': 'contorno', 'id': 1}},
        {'command': 'G1', 'param': {'start': Vec3(1, 1, 0), 'end': Vec3(2, 2, 0), 'layer': 'contorno', 'id': 2}}
    ]
    initial_point = Vec3(0, 0, 0)
    ordered_list = gcode.order_entity_list(entity_list, initial_point)
    expected = [
        {'command': 'G1', 'param': {'start': Vec3(0, 0, 0), 'end': Vec3(1, 1, 0), 'layer': 'contorno', 'id': 1}},
        {'command': 'G1', 'param': {'start': Vec3(1, 1, 0), 'end': Vec3(2, 2, 0), 'layer': 'contorno', 'id': 2}}
    ]
    assert ordered_list == expected


def test_invalid_values():
    gcode = GcodeGenerator()
    try:
        gcode.line_entity(None, Vec3(1, 1, 0), 'contorno', 1)  
    except Exception as e:
        assert isinstance(e, InvalidPointError) 


def test_large_dxf_file():
    gcode = GcodeGenerator()
    for i in range(1000):
        gcode.line_entity(Vec3(i, i, 0), Vec3(i + 1, i + 1, 0), 'contorno', i)
    assert len(gcode.entity_list) == 1000
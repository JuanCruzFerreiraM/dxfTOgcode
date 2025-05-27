from src.core.gcode_generator import GcodeGenerator
from ezdxf.math import Vec3
import math as m

def test_line_entity():
        gcode = GcodeGenerator()
        ps = Vec3(0,0,0)
        pe = Vec3(1.0,1.0,0)
        result = [{
            'command': 'G1',
            'param': {
                'start': ps,
                'end': pe
            }
        }]
        gcode.line_entity(ps,pe)
        assert gcode.entity_list == result
        ps = Vec3(0,0,0)
        pe = Vec3(1000.0,155.0,0)
        result.append ({
            'command': 'G1',
            'param': {
                'start': ps,
                'end': pe
            }
        })
        gcode.line_entity(ps,pe)


def test_arc_entity():
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
            'value': 3 #giramos de 45 a 90 ccw
        }
    })
    gcode.arc_entity(center,radius,alpha,beta)
    assert result == gcode.entity_list
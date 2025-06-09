import ezdxf
from ezdxf.math import Vec3

def create_square(dwg, insert_point: Vec3, size=4, spacing=0.5):
    msp = dwg.modelspace()
    x0, y0 = insert_point.x, insert_point.y
    x1, y1 = x0 + size, y0 + size

    # Contorno (horario)
    msp.add_line((x0, y0), (x1, y0))
    msp.add_line((x1, y0), (x1, y1))
    msp.add_line((x1, y1), (x0, y1))
    msp.add_line((x0, y1), (x0, y0))

    # Zigzag de relleno
    ys = y0
    ye = ys + spacing
    toggle = True
    while ys < y1:
        if toggle:
            msp.add_line((x0, ys), (x1, ye))
        else:
            msp.add_line((x1, ys), (x0, ye))
        ys = ye
        ye = ye + spacing
        toggle = not toggle

doc = ezdxf.new(dxfversion="R2010")
create_square(doc, Vec3(10, 10, 0))
create_square(doc, Vec3(20, 10, 0))
create_square(doc, Vec3(30, 10, 0))

doc.saveas("outputs/dxf/3_squares_zigzag.dxf")

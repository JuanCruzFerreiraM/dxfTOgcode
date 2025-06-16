import ezdxf

def crear_cuadrado_con_zigzag_diagonal():
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    # Esquinas del cuadrado 4x4 desde (1,1)
    p1 = (1, 1)
    p2 = (5, 1)
    p3 = (5, 5)
    p4 = (1, 5)

    # Crear layers
    if "perimetro" not in doc.layers:
        doc.layers.new(name="perimetro", dxfattribs={'color': 7})
    if "relleno" not in doc.layers:
        doc.layers.new(name="relleno", dxfattribs={'color': 3})

    # Dibujar perímetro en layer "perimetro"
    msp.add_line(p1, p2, dxfattribs={'layer': 'perimetro'})
    msp.add_line(p2, p3, dxfattribs={'layer': 'perimetro'})
    msp.add_line(p3, p4, dxfattribs={'layer': 'perimetro'})
    msp.add_line(p4, p1, dxfattribs={'layer': 'perimetro'})

    # Crear zigzag diagonal desde p1 a p3
    step = 0.4
    x_start = p1[0]
    y_start = p1[1]
    x_end = p3[0]
    y_end = p3[1]

    # El zigzag conectará la línea desde (x_start,y_start) a (x_end,y_end)
    # Con saltos alternados en X y Y para formar el zigzag diagonal

    points = []
    toggle = True
    current_x = x_start
    current_y = y_start

    points.append((current_x, current_y))

    while current_x < x_end and current_y < y_end:
        if toggle:
            current_x = min(current_x + step, x_end)
            points.append((current_x, current_y))
        else:
            current_y = min(current_y + step, y_end)
            points.append((current_x, current_y))
        toggle = not toggle

    # Dibujar líneas conectando los puntos en zigzag
    for i in range(len(points) - 1):
        msp.add_line(points[i], points[i+1], dxfattribs={'layer': 'relleno'})

    # Guardar archivo
    doc.saveas("outputs/dxf/cuadrado_con_zigzag_diagonal.dxf")
    print("Archivo 'cuadrado_con_zigzag_diagonal.dxf' creado.")

crear_cuadrado_con_zigzag_diagonal()

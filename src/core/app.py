from pathlib import Path
from src.core.dxf_parser import generate_entity_list
from src.core.gcode_generator import GcodeGenerator
from src.core.machine_handler import MachineHandler
from ezdxf.math import Vec3;
def main():
    output_dir = Path("outputs/texts")
    output_dir.mkdir(parents=True, exist_ok=True)  
    output_name = input('Ingrese el nombre del archivo g-code\n')
    output_filename = output_dir / output_name
    input_filename = input('Ingrese el path completo del archivo que quiere cargar\n')
    gcode_generator = GcodeGenerator()
    generate_entity_list(input_filename,gcode_generator)
    initial_point = Vec3(0,0,0)
    main_list = gcode_generator.get_entity_list()
    entitys = gcode_generator.order_entity_list(main_list,initial_point)
    machine = MachineHandler()
    layers = 2 #esto entra por paremetro
    for i in range(0,2):
        machine.generate_gcode(entitys, output_filename, i, 2)
        nextPoint = Vec3(machine.x,machine.y,machine.z) #deberiamos proteger los accesos con get.
        entitys = gcode_generator.order_entity_list(main_list,nextPoint)
    
    
if __name__ == "__main__":
    main()    
    
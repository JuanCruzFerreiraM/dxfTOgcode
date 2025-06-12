from pathlib import Path
from src.core.dxf_parser import generate_entity_list
from src.core.gcode_generator import GcodeGenerator
from src.core.machine_handler import MachineHandler
def main():
    output_dir = Path("outputs/texts")
    output_dir.mkdir(parents=True, exist_ok=True)  
    output_name = input('Ingrese el nombre del archivo g-code\n')
    output_filename = output_dir / output_name
    input_filename = input('Ingrese el path completo del archivo que quiere cargar\n')
    gcode_generator = GcodeGenerator()
    generate_entity_list(input_filename,gcode_generator)
    entitys = gcode_generator.order_entity_list()
    machine = MachineHandler(layers=2)
    machine.generate_gcode(entitys, output_filename)
    
    
    
if __name__ == "__main__":
    main()    
    
import unittest
from src.core.gcode_generator import line_movement

class TestLineMovement(unittest.TestCase):
    def test_line_movement(self):
        result = line_movement(0,0,0,1,1,1)
        valid = 'G0 X0 Y0 Z0\nG1 X1 Y1 Z1'
        self.assertEqual(result, valid)
        
        result = line_movement(0,0,0,-1,-1,-1)
        valid = 'G0 X0 Y0 Z0\nG1 X-1 Y-1 Z-1'
        self.assertEqual(result, valid)
        
        #En principio con esos son validos.
        
        
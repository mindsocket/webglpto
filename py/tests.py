import unittest
import app

class TestPTOParser(unittest.TestCase):

    def setUp(self):
        pass

    def test_load(self):
        pto = app.load_pto('../pto/PA030369-PA030374.pto')
        self.assertEqual(pto.i[0].n.value, 'PA030369.JPG', '''Image filename''')
        
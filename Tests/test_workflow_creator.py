import pdb
import sys
import json
import os
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(1, '/data/git/nomad/')

from nomad.client import parse, normalize_all
from Tools.PrepareUpload.workflow_eos_creator import parse_outcar,  create_eos_workflow, get_energies_from_list_outcars
from nomad.utils import dump_json
import glob

first_outcar = 'ExampleUpload/R-AAAAAAAABBB/volume_relaxed/xc=PBE-PAW.E=450.dk=0.020/OUTCAR.1.000'
outcars_dir = os.path.dirname(first_outcar)
import unittest

class TestPrepareUploads(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.outcars_list = glob.glob(outcars_dir+'/OUTCAR**')

    def no_test_get_evcurve(self):
        volumes, energies = get_energies_from_list_outcars(self.outcars_list)
        self.assertTrue(len(energies) > 0)
        self.assertTrue(len(volumes) > 0)

    def test_create_eos_workflow(self):
        archive = create_eos_workflow(outcars_dir)
        with open(os.path.join(outcars_dir, 'test_archive.json'), 'w') as f:
            json.dump(archive.m_to_dict(), f)



        






if __name__ == '__main__':
    unittest.main()


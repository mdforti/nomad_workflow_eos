import pdb
import sys
import json
import os
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
import socket
hostname = socket.gethostname()
if 'aberdeen'  in hostname.lower():
    sys.path.insert(1, '/scratch/git/nomad/')
elif 'laptop'  in hostname.lower():
    sys.path.insert(1, '/data/git/nomad/')
sys.path.insert(1, '/data/git/nomad/')

from nomad.client import parse, normalize_all
from Tools.PrepareUpload.workflow_eos_creator import parse_outcar,  create_eos_workflow, get_energies_from_list_outcars, run_normalize
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

    def no_test_create_eos_workflow(self):
        archive_dict = create_eos_workflow(outcars_dir, structure_name = 'R')
        with open(os.path.join(outcars_dir, 'test_archive.json'), 'w') as f:
            json.dump(archive_dict, f)

#    def test_resulting_archive(self):
#        parsed_outcar = parse(os.path.join(outcars_dir, 'OUTCAR.1.000_0_archive.json'))
#        normalized_outcar = [] 
#        for parsed in parsed_outcar:
#            run_normalize(parsed) 



        






if __name__ == '__main__':
    unittest.main()


import sys
import json
import os
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(1, '/data/Anaconda/ml_datasets/lib/python3.9/site-packages')
from nomad.client import parse, normalize_all
from nomad.client.processing import parse

#from nomad.archive import
#from nomad.client import parse, normalize_all

from Tools.PrepareUpload.PrepareUpload import UploadMaker

first_outcar = 'ExampleUpload/R-AAAAAAAABBB/volume_relaxed/xc=PBE-PAW.E=450.dk=0.020/OUTCAR.0.975'
import glob
import unittest
class TestPrepareUploads(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.uploader = UploadMaker()


    def test_makes_anarchive(self):
        firstdir = os.path.dirname(self.uploader.volume_energy_files[0])
        anarchive = self.uploader.parse_outcars(firstdir)
        print(anarchive[0].workflow[0].type )
    





if __name__ == '__main__':
    unittest.main()


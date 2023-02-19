import pdb
import sys
import json
import os
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(1, '/data/git/nomad-FAIR/')

from nomad.client import parse, normalize_all
from nomad.client.processing import parse

#from nomad.archive import
#from nomad.client import parse, normalize_all

from Tools.PrepareUpload.PrepareUpload import UploadMaker

first_outcar = 'ExampleUpload/R-AAAAAAAABBB/volume_relaxed/xc=PBE-PAW.E=450.dk=0.020/OUTCAR.1.000'
import glob
import unittest

class TestPrepareUploads(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.uploader = UploadMaker()


    def test_makes_anarchive(self):
        firstdir = os.path.dirname(self.uploader.volume_energy_files[0])
        archives = self.uploader.parse_outcar(firstdir)
        self.assertTrue(len(archives)>0)

    def test_makes_entry_archive(self):
        entry_archive =  self.uploader.init_entry_archive()
        self.assertTrue(hasattr(entry_archive, 'run'))
        print(entry_archive.run.__dict__.keys())

    def test_defines_a_quantity(self):
        parser = TextParser()
    





if __name__ == '__main__':
    unittest.main()


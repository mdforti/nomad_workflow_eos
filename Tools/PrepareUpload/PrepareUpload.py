import os
import sys
from nomad.client.processing import parse

root = os.path.dirname(os.path.dirname(__file__))

import glob

class UploadMaker:

    def __init__(self):

        self.volume_energy_files = glob.glob('**/volume-energy.dat', recursive=True)
        self.template_archive_json_file = ''

    
    def parse_outcars(self, thedir:str):
        OUTCARS = glob.glob(thedir+'/OUTCAR*')
        archive = parse(OUTCARS[0], parser_name = 'parsers/vasp')
        return archive




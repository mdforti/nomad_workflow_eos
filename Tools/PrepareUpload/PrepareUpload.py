import os
import sys
#sys.path.insert(0, '/data/git/nomad-lab-1.1.5/')
sys.path.insert(0, '/data/git/nomad-FAIR/')
from nomad.client.processing import parse
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.parsing.file_parser import TextParser, Quantity, ParsePattern,\
    XMLParser, BasicParser
from nomad.datamodel.context import Context, ClientContext
from nomad.datamodel.metainfo.simulation.run import Run, Program
root = os.path.dirname(os.path.dirname(__file__))

import glob

class UploadMaker:

    def __init__(self):

        self.volume_energy_files = glob.glob('**/volume-energy.dat', recursive=True)
        self.template_archive_json_file = ''

    
    def init_entry_archive(self, mainfile_out = 'archive.json'):
        this_archive =  EntryArchive()
        run = this_archive.m_create(Run)
        this_archive.metadata = EntryMetadata(m_context=ClientContext(local_dir=os.curdir))
        this_archive.metadata.mainfile = mainfile_out
        return this_archive

    def parse_outcar(self, thedir:str):
        OUTCARS = glob.glob(thedir+'/OUTCAR*')
        archive = parse(OUTCARS[0], parser_name = 'parsers/vasp')
        return archive






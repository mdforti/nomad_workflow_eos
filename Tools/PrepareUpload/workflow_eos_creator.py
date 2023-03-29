import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socket
hostname = socket.gethostname()
if 'aberdeen'  in hostname.lower():
    sys.path.insert(1, '/scratch/git/nomad/')
elif 'laptop'  in hostname.lower():
    sys.path.insert(1, '/data/git/nomad/')

from nomad.client.processing import parse
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.parsing.file_parser import TextParser, Quantity, ParsePattern,\
    XMLParser, BasicParser
from nomad.datamodel.context import Context, ClientContext
from nomad.normalizing import normalizers
from nomad.datamodel.metainfo.simulation.run import Run, Program
import glob 
from nomad.units import ureg
from nomad.datamodel.metainfo.workflow import (
    GeometryOptimization,
    EquationOfState,
    EOSFit
)
from nomad.datamodel.metainfo.workflow  import Workflow
from nomad.datamodel.metainfo.workflow2  import Workflow as Workflow2
#from nomad.datamodel.metainfo.workflow import Workflow

#from nomad.normalizing.workflow import Workflow

import numpy as np
import pdb
import shutil

from ase.eos import EquationOfState as ASE_EOS

from nomad.datamodel.results import Symmetry
import json

def parse_outcar(theoutcar:str, prototype_structure = None) -> EntryArchive:
    archives = parse(theoutcar)
    normalized_archives = [run_normalize(archive) for archive in archives]
    return normalized_archives

def get_template_from_min_energy(list_of_outcars, list_of_energies, prototype_structure = None):
    min_energy_pos = np.argmin(list_of_energies) 
    template_archive = parse_outcar(list_of_outcars[min_energy_pos] , prototype_structure = prototype_structure)
    template_archive[0].results.material.symmetry.m_update_from_dict({ 'structure_name': prototype_structure })
    template_archive[0].metadata.m_update_from_dict({'quantities':[ 'results.material.symmetry.structure_name' ]})
    return template_archive

def make_eos_from_ev_curve(thevolumes : list, theenergies: list) -> EquationOfState:
    equation_of_state = EquationOfState(
        volumes=thevolumes,
        energies=theenergies
        )
    # numbers are unit conversion
    BM = ASE_EOS([ v *1e30  for v in thevolumes ],[ e * 6.241509e+18 for e in  theenergies ], eos='birchmurnaghan')
    v0, e0, B = BM.fit()
    eos_fit = equation_of_state.m_create(EOSFit)
    eos_fit.function_name = 'murnaghan'
    eos_fit.fitted_energies = theenergies
    eos_fit.bulk_modulus = B * 1e11
    return equation_of_state

def make_reference_strings(list_of_outcars : list) -> list:
    """
    takes a list of OUTCAR paths and build the list of calculation_reference for nomad workflow
    """
    list_of_references = ['../upload/archive/mainfile/'+os.path.basename(outcar)+'#/run/calculation/0' for outcar in list_of_outcars]
    return list_of_references

def get_input_outcar(OUTCAR_dir: str) -> str:
    RLX_OUTCAR_DIR  = os.path.dirname(  os.path.dirname(OUTCAR_dir) )
    RLX_OUTCAR = glob.glob(os.path.join(RLX_OUTCAR_DIR,'relax', '**', 'OUTCAR*'))
    for outcar in RLX_OUTCAR:
        if outcar.endswith('.gz') :
            wait = os.popen(f'gunzip --keep  -f {outcar}').read()
            outcar = outcar[:-3]
    RLX_OUTCAR = [outcar for outcar in sorted( RLX_OUTCAR ) if not outcar.endswith('gz')]
    return RLX_OUTCAR


def create_eos_workflow(OUTCAR_dir : str, structure_name : str = None) -> EntryArchive:
    """Entry with mechanical properties."""
    OUTCARS = glob.glob(OUTCAR_dir+'/OUTCAR.[0-1].*')
    OUTCARS = [thisfile for thisfile in OUTCARS if not thisfile.endswith('json')]
    OUTCAR_BASENAMES = [os.path.basename(thisoutcar) for thisoutcar in OUTCARS]
    RLX_OUTCAR = get_input_outcar(OUTCAR_dir)
    rlx_archive = parse_outcar(RLX_OUTCAR[0])
    last_rlx_task = len(rlx_archive[0].workflow2.tasks)-1
    for i, outcarrlx in enumerate( RLX_OUTCAR ):
        if not outcarrlx.endswith('gz'):
            shutil.copyfile(outcarrlx, os.path.dirname(OUTCARS[0])+f'/OUTCAR-{i}-RLX')
    list_of_archives = [] 
    for thisoutcar in OUTCARS: 
        if thisoutcar.endswith('json'):
            continue
        print(thisoutcar)
        list_of_archives.append(parse_outcar(thisoutcar)) #, prototype_structure = structure_name) )
    list_of_volumes, list_of_energies = get_energies_from_list_outcars(list_of_archives)
#    templates = EntryArchive() #
    templates = get_template_from_min_energy(OUTCARS, list_of_energies)[0]
    templates.workflow = []
    workflow = templates.m_create(Workflow)
    # EOS workflow
    workflow.type = 'equation_of_state'
    workflow.equation_of_state = make_eos_from_ev_curve(list_of_volumes, list_of_energies)
    templates.m_create(Workflow2)
    templates.workflow2.name = "Full Optimization"
    normalized_workflow = run_normalize(templates)
    archive_dict = templates.m_to_dict()
    list_of_reference_strings = make_reference_strings(OUTCARS) # [archive[0].run[0].calculation[0] for archive in list_of_archives]
    archive_dict['workflow'][-1]['calculations_ref'] = list_of_reference_strings
    archive_dict['workflow2']['tasks'] = [
            {'name': f'point_{i}', 
#                'inputs' : [{'name': 'Optimized Structure', 'section': '#/workflow2/inputs/0'}],
                'inputs' : [ {'name': 'Optimized Structure', 'section' : f'../upload/archive/mainfile/OUTCAR-0-RLX#/workflow2/tasks/{last_rlx_task}/outputs/1' } ], 
#                'inputs' : [ {'name': 'Optimized Structure', 'section' : '../upload/archive/mainfile/OUTCAR-0-RLX#/run/0/calculation/-1/system_ref'} ], 
                'outputs' : [{'name': f'strained_{i}', 'section': f'../upload/archive/mainfile/{thisoutcar}#/workflow2/tasks/0/outputs/0'}]
            }
            for i, thisoutcar in enumerate(OUTCAR_BASENAMES)
            ] 
    archive_dict['workflow2']['tasks'] += [{
        'name': 'ev_curve', 
        'inputs': [{'name' : f'strained_{i}', 'section': f'../upload/archive/mainfile/{thisoutcar}#/workflow2/tasks/0/outputs/0'}
            for i, thisoutcar  in enumerate(OUTCAR_BASENAMES)], 
        'outputs' : [{'name': 'fitted ev curve', 'section' : '#/workflow2/outputs/0'}]
        }]
#    archive_dict['workflow2']['inputs'] =[ {'name': 'Optimized Structure', 'section' : '../upload/archive/mainfile/OUTCAR-0-RLX#/run/0/calculation/-1/system_ref'} ], 
    archive_dict['workflow2']['inputs'] = [{'name': 'Optimized Structure', 'section' : f'../upload/archive/mainfile/OUTCAR-0-RLX#/workflow2/tasks/{last_rlx_task}/outputs/1' }]

    archive_dict['workflow2']['outputs'] = [{'name': 'eos_fit', 'section' : '#/workflow/0/equation_of_state/eos_fit' }]
    return archive_dict

def get_energies_from_list_outcars(list_of_archives) -> list:
    list_of_energies = [archives[0].run[0].calculation[0].energy.total.value._magnitude for archives in list_of_archives]
    list_of_volumes = [archives[0].results.properties.structures.structure_original.cell_volume._magnitude for archives in list_of_archives]
    return  list_of_volumes, list_of_energies

def run_normalize(entry_archive: EntryArchive) -> EntryArchive:
    for normalizer_class in normalizers:
        normalizer = normalizer_class(entry_archive)
        normalizer.normalize()
    return entry_archive


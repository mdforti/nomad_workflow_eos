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
from nomad.datamodel.metainfo.simulation.workflow import EquationOfState, EOSFit, EquationOfStateResults
from nomad.datamodel.metainfo.workflow  import Workflow
from nomad.datamodel.results import Properties, Results
#from nomad.datamodel.metainfo.workflow import Workflow

#from nomad.normalizing.workflow import Workflow

import numpy as np
import pdb
import shutil


from ase.eos import birchmurnaghan
from scipy.optimize import curve_fit
    

from nomad.datamodel.results import Symmetry
import json

import warnings
warnings.filterwarnings("ignore")

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
    #    BM = ASE_EOS(
    converted_volumes = [ ureg.convert(v,  'meter ** 3', 'angstrom ** 3')  for v in thevolumes ]
    converted_energies  = [ ureg.convert(e, 'joule', 'eV')  for e in  theenergies ]
    #        eos='birchmurnaghan')
    minenergy_at = np.argmin(converted_energies)
    p0 = [converted_energies[minenergy_at], 1, 1, converted_volumes[minenergy_at] ]
    ( e0, B, BP, v0 ), _  = curve_fit(birchmurnaghan, converted_volumes, converted_energies, p0 = p0)
#    eos_fit = equation_of_state.m_create(EOSFit)
#    eos_fit.function_name = 'murnaghan'
#    eos_fit.fitted_energies = theenergies
#    eos_fit.bulk_modulus = B * 1e11
    equation_of_state_results = EquationOfStateResults(
        volumes=thevolumes,
        energies=theenergies, 
        )
    # numbers are unit conversion
    equation_of_state = EquationOfState(results = equation_of_state_results)
    eos_fit = equation_of_state.results.m_create(EOSFit)

    eos_fit.equilibrium_volume = ureg.convert(v0, 'angstrom ** 3', 'meter ** 3')
    eos_fit.equilibrium_energy = ureg.convert(e0, 'eV', 'joule')
    eos_fit.bulk_modulus = ureg.convert(B, 'GPa', 'Pa')
    eos_fit.function_name = 'murnaghan'
    fitted_energies = np.array([ birchmurnaghan(v, e0, B, BP, v0) for v in converted_volumes ])
    rms = np.sqrt( np.sum(fitted_energies**2) )
    fitted_energies_converted = [ ureg.convert(e, 'eV', 'joule') for e in fitted_energies ]
    eos_fit.rms_error = ureg.convert(rms, 'eV', 'joule')
    
    eos_fit.fitted_energies = fitted_energies_converted
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
            with os.popen(f'gunzip --keep  -f {outcar}')  as f:
                output = f.readlines()
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
#    templates.workflow = []
#    workflow = templates.m_create(Workflow)
    # EOS workflow
#    workflow.type = 'equation_of_state'
    templates.workflow2 = make_eos_from_ev_curve(list_of_volumes, list_of_energies)
    #templates.workflow2 = EquationOfState(
    #        results =EquationOfStateResults(
    #            energies=list_of_energies,
    #            volumes = list_of_volumes, 
    #            )
    #        )#make_eos_from_ev_curve(list_of_volumes, list_of_energies)
    list_of_reference_strings = make_reference_strings(OUTCARS) # [archive[0].run[0].calculation[0] for archive in list_of_archives]
    normalized_workflow = run_normalize(templates)
    archive_dict = templates.m_to_dict()
    archive_dict['workflow2']['results']['calculations_ref'] = list_of_reference_strings
    archive_dict['workflow2']['tasks'] = [
            {'name': f'point_{i}', 
                'inputs' : [ {'name': 'Optimized Structure', 'section' : f'../upload/archive/mainfile/OUTCAR-0-RLX#/workflow2/tasks/{last_rlx_task}/outputs/1' } ], 
                'outputs' : [{'name': f'strained_{i}', 'section': f'../upload/archive/mainfile/{thisoutcar}#/run/0/calculation/'}] #/workflow2/tasks/0/outputs/0'}]
            }
            for i, thisoutcar in enumerate(OUTCAR_BASENAMES)
            ] 
    archive_dict['workflow2']['tasks'] += [{
        'name': 'ev_curve', 
        'inputs': [{'name' : f'strained_{i}', 'section': f'../upload/archive/mainfile/{thisoutcar}#/run/0/calculation/'}  #/workflow2/tasks/0/outputs/0'}
            for i, thisoutcar  in enumerate(OUTCAR_BASENAMES)], 
        'outputs' : [{'name': 'fitted ev curve', 'section' : '#/workflow2/results/eos_fit'}]
        }]
    archive_dict['workflow2']['inputs'] = [{'name': 'Optimized Structure', 'section' : f'../upload/archive/mainfile/OUTCAR-0-RLX#/workflow2/tasks/{last_rlx_task}/outputs/1' }]
#
    archive_dict['workflow2']['outputs'] = [{'name': 'eos_fit', 'section' : '#/workflow2/results/eos_fit/' }]
    return archive_dict

def get_energies_from_list_outcars(list_of_archives) -> list:
    list_of_energies = [archives[0].run[0].calculation[0].energy.total.value._magnitude for archives in list_of_archives]
    list_of_volumes = [archives[0].results.material.topology[0].cell.volume._magnitude for archives in list_of_archives]
    return  list_of_volumes, list_of_energies

def run_normalize(entry_archive: EntryArchive) -> EntryArchive:
    for normalizer_class in normalizers:
        normalizer = normalizer_class(entry_archive)
        normalizer.normalize()
    return entry_archive


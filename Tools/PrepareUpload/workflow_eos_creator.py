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
    DiffusionConstantValues,
    IntegrationParameters,
    MeanSquaredDisplacement,
    MeanSquaredDisplacementValues,
    MolecularDynamicsResults,
    RadialDistributionFunction,
    RadialDistributionFunctionValues,
    GeometryOptimization,
    Elastic,
    MolecularDynamics,
    EquationOfState,
    EOSFit
)
#from nomad.datamodel.metainfo.workflow2 import Workflow
from nomad.datamodel.metainfo.workflow import Workflow
#from nomad.normalizing.workflow import Workflow

import numpy as np
import pdb

from ase.eos import EquationOfState as ASE_EOS

from nomad.datamodel.results import Symmetry
import json

def parse_outcar(theoutcar:str, prototype_structure = None) -> EntryArchive:
    archives = parse(theoutcar)
    normalized_archives = [run_normalize(archive) for archive in archives]
    for i, normalized_archive in enumerate(normalized_archives):
#        symmetry = normalized_archive.results.material.symmetry.m_to_dict()
        normalized_archive.results.material.symmetry.m_update_from_dict({'structure_name': prototype_structure})
        normalized_archive.metadata.m_update_from_dict({'quantities':[ 'results.material.symmetry.structure_name' ]})
        this_dict = normalized_archive.m_to_dict()
        filename = theoutcar+f'_{i:d}_archive.json'
        with open(filename, 'w') as f:
            json.dump(this_dict, f)
#    normalized_archives[0].results.material.structre_name='R'
    
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
    eos_fit.bulk_modulus = B
    return equation_of_state

def make_reference_strings(list_of_outcars : list) -> list:
    """
    takes a list of OUTCAR paths and build the list of calculation_reference for nomad workflow
    """
    #../uploads/archive/mainfile/
    ##/run/calculation/0
    list_of_references = ['../uploads/archive/mainfile/'+os.path.basename(outcar)+'#/run/calculation/0' for outcar in list_of_outcars]
    return list_of_references



def create_eos_workflow(OUTCAR_dir : str, structure_name : str = None) -> EntryArchive:
    """Entry with mechanical properties."""
    OUTCARS = glob.glob(OUTCAR_dir+'/OUTCAR*')
    list_of_archives = [parse_outcar(thisoutcar, prototype_structure = structure_name) for thisoutcar in OUTCARS]
    list_of_volumes, list_of_energies = get_energies_from_list_outcars(list_of_archives)
    templates = get_template_from_min_energy(OUTCARS, list_of_energies)
    workflow = templates[0].m_create(Workflow)
    # EOS workflow
    workflow.type = 'equation_of_state'
    workflow.equation_of_state = make_eos_from_ev_curve(list_of_volumes, list_of_energies)
    normalized_workflow = run_normalize(templates[0])
    archive_dict = templates[0].m_to_dict()
    archive_dict['workflow'][-1]['calculations_ref'] = make_reference_strings(OUTCARS) # [archive[0].run[0].calculation[0] for archive in list_of_archives]
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



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
from nomad.datamodel.metainfo.workflow2 import Workflow

import numpy as np
import pdb

def parse_outcar(theoutcar:str) -> EntryArchive:
    archives = parse(theoutcar)
    return [run_normalize(archive) for archive in archives]

def create_eos_workflow(OUTCAR_dir):
    """Entry with mechanical properties."""

    OUTCARS = glob.glob(OUTCAR_dir+'/OUTCAR*')
    list_of_volumes, list_of_energies = get_energies_from_list_outcars(OUTCARS)
    min_energy_pos = np.argmin(list_of_energies) 
    templates = parse_outcar(OUTCARS[min_energy_pos])
    workflow = templates[0].m_create(Workflow)
    # EOS workflow
    workflow.type = 'equation_of_state'
    equation_of_state = EquationOfState(
        volumes=list_of_volumes,
        energies=list_of_energies
    )
    eos_fit = equation_of_state.m_create(EOSFit)
    eos_fit.function_name = 'murnaghan'
    eos_fit.fitted_energies = list_of_energies
    eos_fit.bulk_modulus = 10000
    workflow.equation_of_state = equation_of_state
    return run_normalize(templates[0])

def get_energies_from_list_outcars(list_of_outcars):
    list_of_archives = [parse_outcar(thisoutcar) for thisoutcar in list_of_outcars]
    list_of_energies = [archives[0].run[0].calculation[0].energy.total.value._magnitude for archives in list_of_archives]
#    list_of_lattice_vectors = [archives[0].run[0].system[0].atoms.lattice_vectors for archives in list_of_archives]
    list_of_volumes = [archives[0].results.properties.structures.structure_original.cell_volume._magnitude for archives in list_of_archives]
    return  list_of_volumes, list_of_energies

def run_normalize(entry_archive: EntryArchive) -> EntryArchive:
    for normalizer_class in normalizers:
        normalizer = normalizer_class(entry_archive)
        normalizer.normalize()
    return entry_archive



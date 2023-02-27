import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
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

def parse_outcar(theoutcar:str) -> EntryArchive:
    archives = parse(theoutcar)
    return [run_normalize(archive) for archive in archives]

def get_template_from_min_energy(list_of_outcars, list_of_energies):
    min_energy_pos = np.argmin(list_of_energies) 
    return parse_outcar(list_of_outcars[min_energy_pos])

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


def create_eos_workflow(OUTCAR_dir) -> EntryArchive:
    """Entry with mechanical properties."""
    OUTCARS = glob.glob(OUTCAR_dir+'/OUTCAR*')
    list_of_archives = [parse_outcar(thisoutcar) for thisoutcar in OUTCARS]
    list_of_volumes, list_of_energies = get_energies_from_list_outcars(list_of_archives)
    templates = get_template_from_min_energy(OUTCARS, list_of_energies)
    workflow = templates[0].m_create(Workflow)
    # EOS workflow
    workflow.type = 'equation_of_state'
    workflow.equation_of_state = make_eos_from_ev_curve(list_of_volumes, list_of_energies)
    workflow.calculations_ref = [archive[0].run[0].calculation[0] for archive in list_of_archives]
    return run_normalize(templates[0])

def get_energies_from_list_outcars(list_of_archives) -> list:
#    list_of_archives = [parse_outcar(thisoutcar) for thisoutcar in list_of_outcars]
    list_of_energies = [archives[0].run[0].calculation[0].energy.total.value._magnitude for archives in list_of_archives]
#    list_of_lattice_vectors = [archives[0].run[0].system[0].atoms.lattice_vectors for archives in list_of_archives]
    list_of_volumes = [archives[0].results.properties.structures.structure_original.cell_volume._magnitude for archives in list_of_archives]
    return  list_of_volumes, list_of_energies

def run_normalize(entry_archive: EntryArchive) -> EntryArchive:
    for normalizer_class in normalizers:
        normalizer = normalizer_class(entry_archive)
        normalizer.normalize()
    return entry_archive



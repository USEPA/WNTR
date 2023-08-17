import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr
import wntr.reaction
import sympy

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
test_data_dir = join(testdir, "data_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

class Test(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        pass

    @classmethod
    def tearDownClass(self):
        pass

    def test_RxnVariable_reserved_name_exception(self):
        self.assertRaises(ValueError, wntr.reaction.model.RxnVariable, 'I')
        self.assertRaises(ValueError, wntr.reaction.model.RxnSpecies, 'Ff', 'mg')
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, 'D', 'mg')
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, 'Q', 'mg')
        self.assertRaises(ValueError, wntr.reaction.model.RxnCoefficient, 'Re', 0.52)

    def test_RxnVariable_direct_instantiation_exceptions(self):
        self.assertRaises(NotImplementedError, wntr.reaction.model.RxnVariable, 'Test')
        self.assertRaises(NotImplementedError, wntr.reaction.model.RxnSpecies, 'Test', 'mg/L')
        self.assertRaises(NotImplementedError, wntr.reaction.model.RxnCoefficient, 'Test', 0.524)

    def test_RxnVariable_symbols_and_sympy(self):
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        symbol1 = sympy.symbols('Cl')
        self.assertEqual(species1.get_symbol(), symbol1)

        const1 = wntr.reaction.model.Constant('Kb', 0.482)
        symbol2 = sympy.symbols('Kb')
        self.assertEqual(const1.get_symbol(), symbol2)

    def test_RxnVariable_values(self):
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        self.assertEqual(species1.get_value(), species1.value)
        self.assertRaises(TypeError, species1.get_value, pipe='blah')
        const1 = wntr.reaction.model.Constant('Kb', 0.482, note='test')
        self.assertEqual(const1.get_value(), const1.value)

    def test_RxnVariable_string_functions(self):
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        self.assertEqual(str(species1), 'Cl')
        self.assertEqual(species1.to_msx_string(), 'BULK Cl mg  ;')
        species2 = wntr.reaction.model.WallSpecies('Cl', 'mg', 0.01, 0.0001, note='Testing stuff')
        self.assertEqual(species2.to_msx_string(), 'WALL Cl mg 0.01 0.0001 ;Testing stuff')

    def test_RxnSpecies_tolerances(self):
        #"""RxnSpecies(*s) tolerance settings"""
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        species2 = wntr.reaction.model.WallSpecies('Cl', 'mg', 0.01, 0.0001, note='Testing stuff')
        self.assertIsNone(species1.get_tolerances())
        self.assertIsNotNone(species2.get_tolerances())
        self.assertTupleEqual(species2.get_tolerances(), (0.01, 0.0001))
        self.assertRaises(TypeError, species1.set_tolerances, None, 0.0001)
        self.assertRaises(ValueError, species1.set_tolerances, -0.51, 0.01)
        self.assertRaises(ValueError, species1.set_tolerances, 0.0, 0.0)
        species1.set_tolerances(0.01, 0.0001)
        self.assertEqual(species1.Atol, 0.01)
        self.assertEqual(species1.Rtol, 0.0001)
        species1.set_tolerances(None, None)
        self.assertIsNone(species1.Atol)
        self.assertIsNone(species1.Rtol)
        species2.clear_tolerances()
        self.assertIsNone(species1.Atol)
        self.assertIsNone(species1.Rtol)
        self.assertIsNone(species2.get_tolerances())

    def test_BulkSpecies_creation(self):
        #"""BlukSpecies object creation (direct instantiation)"""
        self.assertRaises(TypeError, wntr.reaction.model.BulkSpecies, 'I')
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, 'I', 'mg')
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, 'Cl', 'mg', 0.01)
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, 'Cl', 'mg', None, 0.01)
        species = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        self.assertEqual(species.name, 'Cl')
        self.assertEqual(species.value, 'mg')
        self.assertEqual(species.value, species.unit)
        self.assertEqual(species.species_type, wntr.reaction.model.VarType.Bulk)
        self.assertIsNone(species.Atol)
        self.assertIsNone(species.Rtol)
        self.assertIsNone(species.note)
        species = wntr.reaction.model.BulkSpecies('Cl', 'mg', 0.01, 0.0001, note='Testing stuff')
        self.assertEqual(species.variable_type, wntr.reaction.model.VarType.Bulk)
        self.assertEqual(species.name, 'Cl')
        self.assertEqual(species.value, 'mg')
        self.assertEqual(species.Atol, 0.01)
        self.assertEqual(species.Rtol, 0.0001)
        self.assertEqual(species.note, 'Testing stuff')

    def test_WallSpecies_creation(self):
        #"""WallSpecies object creation (direct instantiation)"""
        self.assertRaises(TypeError, wntr.reaction.model.WallSpecies, 'I')
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, 'I', 'mg')
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, 'Cl', 'mg', 0.01)
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, 'Cl', 'mg', None, 0.01)
        species = wntr.reaction.model.WallSpecies('Cl', 'mg')
        self.assertEqual(species.name, 'Cl')
        self.assertEqual(species.value, 'mg')
        self.assertEqual(species.value, species.unit)
        self.assertEqual(species.species_type, wntr.reaction.model.VarType.Wall)
        self.assertIsNone(species.Atol)
        self.assertIsNone(species.Rtol)
        self.assertIsNone(species.note)
        species = wntr.reaction.model.WallSpecies('Cl', 'mg', 0.01, 0.0001, note='Testing stuff')
        self.assertEqual(species.variable_type, wntr.reaction.model.VarType.Wall)
        self.assertEqual(species.name, 'Cl')
        self.assertEqual(species.value, 'mg')
        self.assertEqual(species.Atol, 0.01)
        self.assertEqual(species.Rtol, 0.0001)
        self.assertEqual(species.note, 'Testing stuff')

    def test_Constant_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.Constant, 'Re')
        self.assertRaises(ValueError, wntr.reaction.model.Constant, 'Re', 2.48)
        const1 = wntr.reaction.model.Constant('Kb', 0.482, note='test')
        # FIXME: Find a way to suppress warning printing
        # self.assertWarns(RuntimeWarning, wntr.reaction.model.Constant, 'Kb1', 0.83, pipe_values={'a',1})
        self.assertEqual(const1.name, 'Kb')
        self.assertEqual(const1.global_value, 0.482)
        self.assertEqual(const1.value, const1.global_value)
        self.assertEqual(const1.coeff_type, wntr.reaction.model.VarType.Constant)
        self.assertEqual(const1.note, 'test')

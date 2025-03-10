import unittest
import warnings
from os.path import abspath, dirname, join

import numpy as np
import pandas as pd
import wntr

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

    def test_ReactionVariable_reserved_name_exception(self):
        self.assertRaises(ValueError, wntr.msx.Species,  "D", 'bulk', "mg")
        self.assertRaises(ValueError, wntr.msx.Species,  "Q", 'wall', "mg")
        self.assertRaises(ValueError, wntr.msx.Constant, "Re", 0.52)
        self.assertRaises(ValueError, wntr.msx.Parameter, "Re", 0.52)
        self.assertRaises(ValueError, wntr.msx.Term, "Re", 0.52)

    def test_RxnVariable_values(self):
        const1 = wntr.msx.Constant("Kb", 0.482, note="test")
        self.assertEqual(const1.value, 0.482)
        param2 = wntr.msx.Parameter("Kb", 0.482, note="test")
        self.assertEqual(param2.global_value, 0.482)

    def test_RxnVariable_string_functions(self):
        species1 = wntr.msx.Species('Cl', 'BULK', "mg")
        const1 = wntr.msx.Constant("Kb", 0.482)
        param1 = wntr.msx.Parameter("Ka", 0.482, note="foo")
        term1 = wntr.msx.Term("T0", "-3.2 * Kb * Cl^2", note="bar")

        self.assertEqual(str(species1), "Cl")
        self.assertEqual(str(const1), "Kb")
        self.assertEqual(str(param1), "Ka")
        self.assertEqual(str(term1), "T0")

    def test_Species_tolerances(self):
        # """RxnSpecies(*s) tolerance settings"""
        species1 = wntr.msx.Species("Cl", 'bulk', "mg")
        species2 = wntr.msx.Species("Cl", 'wall', "mg", 0.01, 0.0001, note="Testing stuff")
        self.assertIsNone(species1.get_tolerances())
        self.assertIsNotNone(species2.get_tolerances())
        self.assertTupleEqual(species2.get_tolerances(), (0.01, 0.0001))
        self.assertRaises(TypeError, species1.set_tolerances, None, 0.0001)
        self.assertRaises(ValueError, species1.set_tolerances, -0.51, 0.01)
        self.assertRaises(ValueError, species1.set_tolerances, 0.0, 0.0)
        species1.set_tolerances(0.01, 0.0001)
        self.assertEqual(species1.atol, 0.01)
        self.assertEqual(species1.rtol, 0.0001)
        species1.set_tolerances(None, None)
        self.assertIsNone(species1.atol)
        self.assertIsNone(species1.rtol)
        species2.clear_tolerances()
        self.assertIsNone(species1.atol)
        self.assertIsNone(species1.rtol)
        self.assertIsNone(species2.get_tolerances())

    def test_BulkSpecies_creation(self):
        # """BlukSpecies object creation (direct instantiation)"""
        self.assertRaises(TypeError, wntr.msx.Species, "Re", 'bulk')
        self.assertRaises(ValueError, wntr.msx.Species, "Re", 'bulk', "mg")
        # self.assertRaises(TypeError, wntr.msx.Species, "Cl", 1, "mg", 0.01, None)
        # self.assertRaises(TypeError, wntr.msx.Species, "Cl", wntr.msx.base.SpeciesType.BULK, "mg", None, 0.01)
        species = wntr.msx.Species("Cl", 1, "mg")
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.units, "mg")
        self.assertEqual(species.species_type, wntr.msx.SpeciesType.BULK)
        self.assertIsNone(species.atol)
        self.assertIsNone(species.rtol)
        self.assertIsNone(species.note)
        species = wntr.msx.Species("Cl",'bulk', "mg", 0.01, 0.0001, note="Testing stuff")
        self.assertEqual(species.species_type, wntr.msx.SpeciesType.BULK)
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.units, "mg")
        self.assertEqual(species.atol, 0.01)
        self.assertEqual(species.rtol, 0.0001)
        self.assertEqual(species.note, "Testing stuff")

    def test_WallSpecies_creation(self):
        # """WallSpecies object creation (direct instantiation)"""
        self.assertRaises(TypeError, wntr.msx.Species, "Re", 'W')
        self.assertRaises(ValueError, wntr.msx.Species, "Re", 'Wall', "mg")
        self.assertRaises(TypeError, wntr.msx.Species, "Cl", 2, "mg", 0.01)
        self.assertRaises(TypeError, wntr.msx.Species, "Cl", 'w', "mg", None, 0.01)
        species = wntr.msx.Species( "Cl", 'w', "mg")
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.units, "mg")
        self.assertEqual(species.species_type, wntr.msx.SpeciesType.WALL)
        self.assertIsNone(species.atol)
        self.assertIsNone(species.rtol)
        self.assertIsNone(species.note)
        species = wntr.msx.Species( "Cl", 'w', "mg", 0.01, 0.0001, note="Testing stuff")
        self.assertEqual(species.species_type, wntr.msx.SpeciesType.WALL)
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.units, "mg")
        self.assertEqual(species.atol, 0.01)
        self.assertEqual(species.rtol, 0.0001)
        self.assertEqual(species.note, "Testing stuff")

    def test_Constant_creation(self):
        self.assertRaises(TypeError, wntr.msx.Constant, "Re")
        self.assertRaises(ValueError, wntr.msx.Constant, "Re", 2.48)
        const1 = wntr.msx.Constant("Kb", 0.482, note="test")
        # FIXME: Find a way to suppress warning printing
        # self.assertWarns(RuntimeWarning, wntr.reaction.Constant, 'Kb1', 0.83, pipe_values={'a',1})
        self.assertEqual(const1.name, "Kb")
        self.assertEqual(const1.value, 0.482)
        self.assertEqual(const1.var_type, wntr.msx.VariableType.CONST)
        self.assertEqual(const1.note, "test")

    def test_Parameter_creation(self):
        self.assertRaises(TypeError, wntr.msx.Parameter, "Re")
        self.assertRaises(ValueError, wntr.msx.Parameter, "Re", 2.48)
        param1 = wntr.msx.Parameter("Kb", 0.482, note="test")
        self.assertEqual(param1.name, "Kb")
        self.assertEqual(param1.global_value, 0.482)
        self.assertEqual(param1.var_type, wntr.msx.VariableType.PARAM)
        self.assertEqual(param1.note, "test")
        # test_pipe_dict = {"PIPE": 0.38}
        # test_tank_dict = {"TANK": 222.23}
        # param2 = wntr.msx.Parameter("Kb", 0.482, note="test", pipe_values=test_pipe_dict, tank_values=test_tank_dict)
        # self.assertDictEqual(param2.pipe_values, test_pipe_dict)
        # self.assertDictEqual(param2.tank_values, test_tank_dict)

    def test_RxnTerm_creation(self):
        self.assertRaises(TypeError, wntr.msx.Term, "Re")
        self.assertRaises(ValueError, wntr.msx.Term, "Re", "1.0*Re")
        term1 = wntr.msx.Term("T0", "-3.2 * Kb * Cl^2", note="bar")
        self.assertEqual(term1.name, "T0")
        self.assertEqual(term1.expression, "-3.2 * Kb * Cl^2")
        self.assertEqual(term1.var_type, wntr.msx.VariableType.TERM)
        self.assertEqual(term1.note, "bar")

    def test_Reaction(self):
        equil1 = wntr.msx.Reaction("Cl", wntr.msx.ReactionType.PIPE, 'equil', "-Ka + Kb * Cl + T0")
        self.assertEqual(equil1.species_name, "Cl")
        self.assertEqual(equil1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(equil1.expression_type, wntr.msx.ExpressionType.EQUIL)
        rate1 = wntr.msx.Reaction("Cl", wntr.msx.ReactionType.TANK, 'rate', "-Ka + Kb * Cl + T0", note="Foo Bar")
        self.assertEqual(rate1.species_name, "Cl")
        self.assertEqual(rate1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(rate1.expression_type, wntr.msx.ExpressionType.RATE)
        self.assertEqual(rate1.note, "Foo Bar")
        formula1 = wntr.msx.Reaction("Cl", wntr.msx.ReactionType.PIPE, 'formula', "-Ka + Kb * Cl + T0")
        self.assertEqual(formula1.species_name, "Cl")
        self.assertEqual(formula1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(formula1.expression_type, wntr.msx.ExpressionType.FORMULA)

    def test_MsxModel_creation_specific_everything(self):
        rxn_model1 = wntr.msx.MsxModel()
        bulk1 = wntr.msx.Species("Cl", 'b', "mg")
        wall1 = wntr.msx.Species("ClOH", 'w', "mg", 0.01, 0.0001, note="Testing stuff")
        const1 = wntr.msx.Constant("Kb", 0.482)
        param1 = wntr.msx.Parameter("Ka", 0.482, note="foo")
        term1 = wntr.msx.Term("T0", "-3.2 * Kb * Cl^2", note="bar")
        equil1 = wntr.msx.Reaction(bulk1, wntr.msx.ReactionType.PIPE, 'equil', "-Ka + Kb * Cl + T0")
        rate1 = wntr.msx.Reaction(bulk1, wntr.msx.ReactionType.TANK, 'rate', "-Ka + Kb * Cl + T0", note="Foo Bar")
        formula1 = wntr.msx.Reaction(wall1, wntr.msx.ReactionType.PIPE, 'formula', "-Ka + Kb * Cl + T0")

        bulk2 = rxn_model1.add_species("Cl", 'bulk', "mg")
        wall2 = rxn_model1.add_species("ClOH", 'wall', "mg", 0.01, 0.0001, note="Testing stuff")
        const2 = rxn_model1.add_constant("Kb", 0.482)
        param2 = rxn_model1.add_parameter("Ka", 0.482, note="foo")
        term2 = rxn_model1.add_term("T0", "-3.2 * Kb * Cl^2", note="bar")
        equil2 = rxn_model1.add_reaction("Cl", "pipe", "equil", "-Ka + Kb * Cl + T0")
        rate2 = rxn_model1.add_reaction("Cl", "tank", wntr.msx.ExpressionType.R, "-Ka + Kb * Cl + T0", note="Foo Bar")
        formula2 = rxn_model1.add_reaction("ClOH", "PIPE", "formula", "-Ka + Kb * Cl + T0")
        self.assertDictEqual(bulk1.to_dict(), bulk2.to_dict())
        self.assertDictEqual(wall1.to_dict(), wall2.to_dict())
        self.assertDictEqual(const1.to_dict(), const2.to_dict())
        self.assertDictEqual(param1.to_dict(), param2.to_dict()) 
        self.assertDictEqual(term1.to_dict(), term2.to_dict())
        self.assertDictEqual(equil1.to_dict(), equil2.to_dict())
        self.assertDictEqual(rate1.to_dict(), rate2.to_dict())
        self.assertDictEqual(formula1.to_dict(), formula2.to_dict())


if __name__ == "__main__":
    unittest.main(verbosity=2)

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

    def test_ReactionVariable_reserved_name_exception(self):
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, "D", "mg")
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, "Q", "mg")
        self.assertRaises(ValueError, wntr.reaction.model.Constant, "Re", 0.52)
        self.assertRaises(ValueError, wntr.reaction.model.Parameter, "Re", 0.52)
        self.assertRaises(ValueError, wntr.reaction.model.OtherTerm, "Re", 0.52)

    def test_RxnVariable_symbols_and_sympy(self):
        species1 = wntr.reaction.model.BulkSpecies("Cl", "mg")
        symbol1 = sympy.symbols("Cl")
        self.assertEqual(species1.symbol, symbol1)

        const1 = wntr.reaction.model.Constant("Kb", 0.482)
        symbol2 = sympy.symbols("Kb")
        self.assertEqual(const1.symbol, symbol2)

        param1 = wntr.reaction.model.Constant("Ka", 0.482)
        symbol3 = sympy.symbols("Ka")
        self.assertEqual(param1.symbol, symbol3)

        term1 = wntr.reaction.model.OtherTerm("T0", "-3.2 * Kb * Cl^2", note="bar")
        symbol4 = sympy.symbols("T0")
        self.assertEqual(term1.symbol, symbol4)

    def test_RxnVariable_values(self):
        const1 = wntr.reaction.model.Constant("Kb", 0.482, note="test")
        self.assertEqual(const1.get_value(), const1.global_value)
        test_pipe_dict = {"PIPE": 0.38}
        test_tank_dict = {"TANK": 222.23}
        param2 = wntr.reaction.model.Parameter("Kb", 0.482, note="test", _pipe_values=test_pipe_dict, _tank_values=test_tank_dict)
        self.assertEqual(param2.get_value(), param2.global_value)
        self.assertEqual(param2.get_value(pipe="PIPE"), test_pipe_dict["PIPE"])
        self.assertEqual(param2.get_value(pipe="FOO"), param2.global_value)
        self.assertEqual(param2.get_value(tank="TANK"), test_tank_dict["TANK"])
        self.assertRaises(TypeError, param2.get_value, pipe="PIPE", tank="TANK")

    def test_RxnVariable_string_functions(self):
        species1 = wntr.reaction.model.BulkSpecies("Cl", "mg")
        species2 = wntr.reaction.model.WallSpecies("Cl", "mg", 0.01, 0.0001, note="Testing stuff")
        const1 = wntr.reaction.model.Constant("Kb", 0.482)
        param1 = wntr.reaction.model.Parameter("Ka", 0.482, note="foo")
        term1 = wntr.reaction.model.OtherTerm("T0", "-3.2 * Kb * Cl^2", note="bar")

        self.assertEqual(str(species1), "Cl")
        self.assertEqual(species1.to_msx_string(), "BULK Cl mg  ;")
        self.assertEqual(species2.to_msx_string(), "WALL Cl mg 0.01 0.0001 ;Testing stuff")
        self.assertEqual(str(const1), "Kb")
        self.assertEqual(str(param1), "Ka")
        self.assertEqual(const1.to_msx_string(), "CONSTANT Kb 0.482 ;")
        self.assertEqual(param1.to_msx_string(), "PARAMETER Ka 0.482 ;foo")
        self.assertEqual(str(term1), "T0")
        self.assertEqual(term1.to_msx_string(), "T0 -3.2 * Kb * Cl^2 ;bar")

    def test_Species_tolerances(self):
        # """RxnSpecies(*s) tolerance settings"""
        species1 = wntr.reaction.model.BulkSpecies("Cl", "mg")
        species2 = wntr.reaction.model.WallSpecies("Cl", "mg", 0.01, 0.0001, note="Testing stuff")
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
        self.assertRaises(TypeError, wntr.reaction.model.BulkSpecies, "Re")
        self.assertRaises(ValueError, wntr.reaction.model.BulkSpecies, "Re", "mg")
        self.assertRaises(TypeError, wntr.reaction.model.BulkSpecies, "Cl", "mg", 0.01)
        self.assertRaises(TypeError, wntr.reaction.model.BulkSpecies, "Cl", "mg", None, 0.01)
        species = wntr.reaction.model.BulkSpecies("Cl", "mg")
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.unit, "mg")
        self.assertEqual(species.var_type, wntr.reaction.model.RxnVarType.BULK)
        self.assertIsNone(species.atol)
        self.assertIsNone(species.rtol)
        self.assertIsNone(species.note)
        species = wntr.reaction.model.BulkSpecies("Cl", "mg", 0.01, 0.0001, note="Testing stuff")
        self.assertEqual(species.var_type, wntr.reaction.model.RxnVarType.BULK)
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.unit, "mg")
        self.assertEqual(species.atol, 0.01)
        self.assertEqual(species.rtol, 0.0001)
        self.assertEqual(species.note, "Testing stuff")

    def test_WallSpecies_creation(self):
        # """WallSpecies object creation (direct instantiation)"""
        self.assertRaises(TypeError, wntr.reaction.model.WallSpecies, "Re")
        self.assertRaises(ValueError, wntr.reaction.model.WallSpecies, "Re", "mg")
        self.assertRaises(TypeError, wntr.reaction.model.WallSpecies, "Cl", "mg", 0.01)
        self.assertRaises(TypeError, wntr.reaction.model.WallSpecies, "Cl", "mg", None, 0.01)
        species = wntr.reaction.model.WallSpecies("Cl", "mg")
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.unit, "mg")
        self.assertEqual(species.var_type, wntr.reaction.model.RxnVarType.WALL)
        self.assertIsNone(species.atol)
        self.assertIsNone(species.rtol)
        self.assertIsNone(species.note)
        species = wntr.reaction.model.WallSpecies("Cl", "mg", 0.01, 0.0001, note="Testing stuff")
        self.assertEqual(species.var_type, wntr.reaction.model.RxnVarType.WALL)
        self.assertEqual(species.name, "Cl")
        self.assertEqual(species.unit, "mg")
        self.assertEqual(species.atol, 0.01)
        self.assertEqual(species.rtol, 0.0001)
        self.assertEqual(species.note, "Testing stuff")

    def test_Constant_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.Constant, "Re")
        self.assertRaises(ValueError, wntr.reaction.model.Constant, "Re", 2.48)
        const1 = wntr.reaction.model.Constant("Kb", 0.482, note="test")
        # FIXME: Find a way to suppress warning printing
        # self.assertWarns(RuntimeWarning, wntr.reaction.model.Constant, 'Kb1', 0.83, pipe_values={'a',1})
        self.assertEqual(const1.name, "Kb")
        self.assertEqual(const1.global_value, 0.482)
        self.assertEqual(const1.get_value(), const1.global_value)
        self.assertEqual(const1.var_type, wntr.reaction.model.RxnVarType.CONST)
        self.assertEqual(const1.note, "test")

    def test_Parameter_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.Parameter, "Re")
        self.assertRaises(ValueError, wntr.reaction.model.Parameter, "Re", 2.48)
        param1 = wntr.reaction.model.Parameter("Kb", 0.482, note="test")
        self.assertEqual(param1.name, "Kb")
        self.assertEqual(param1.global_value, 0.482)
        self.assertEqual(param1.get_value(), param1.global_value)
        self.assertEqual(param1.var_type, wntr.reaction.model.RxnVarType.PARAM)
        self.assertEqual(param1.note, "test")
        test_pipe_dict = {"PIPE": 0.38}
        test_tank_dict = {"TANK": 222.23}
        param2 = wntr.reaction.model.Parameter("Kb", 0.482, note="test", _pipe_values=test_pipe_dict, _tank_values=test_tank_dict)
        self.assertDictEqual(param2.pipe_values, test_pipe_dict)
        self.assertDictEqual(param2.tank_values, test_tank_dict)

    def test_RxnTerm_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.OtherTerm, "Re")
        self.assertRaises(ValueError, wntr.reaction.model.OtherTerm, "Re", "1.0*Re")
        term1 = wntr.reaction.model.OtherTerm("T0", "-3.2 * Kb * Cl^2", note="bar")
        self.assertEqual(term1.name, "T0")
        self.assertEqual(term1.expression, "-3.2 * Kb * Cl^2")
        self.assertEqual(term1.var_type, wntr.reaction.model.RxnVarType.TERM)
        self.assertEqual(term1.note, "bar")

    def test_RxnExpression_strings(self):
        equil1 = wntr.reaction.model.EquilibriumDynamics("Cl", wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")
        rate1 = wntr.reaction.model.RateDynamics("Cl", wntr.reaction.model.RxnLocType.TANK, "-Ka + Kb * Cl + T0", note="Foo Bar")
        formula1 = wntr.reaction.model.FormulaDynamics("Cl", wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")
        self.assertEqual(equil1.to_msx_string(), "EQUIL Cl -Ka + Kb * Cl + T0 ;")
        self.assertEqual(rate1.to_msx_string(), "RATE Cl -Ka + Kb * Cl + T0 ;Foo Bar")
        self.assertEqual(formula1.to_msx_string(), "FORMULA Cl -Ka + Kb * Cl + T0 ;")

    def test_Equilibrium_creation(self):
        equil1 = wntr.reaction.model.EquilibriumDynamics("Cl", wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")
        self.assertEqual(equil1.species, "Cl")
        self.assertEqual(equil1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(equil1.expr_type, wntr.reaction.model.RxnExprType.EQUIL)

    def test_Rate_creation(self):
        rate1 = wntr.reaction.model.RateDynamics("Cl", wntr.reaction.model.RxnLocType.TANK, "-Ka + Kb * Cl + T0", note="Foo Bar")
        self.assertEqual(rate1.species, "Cl")
        self.assertEqual(rate1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(rate1.expr_type, wntr.reaction.model.RxnExprType.RATE)
        self.assertEqual(rate1.note, "Foo Bar")

    def test_Formula_creation(self):
        formula1 = wntr.reaction.model.FormulaDynamics("Cl", wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")
        self.assertEqual(formula1.species, "Cl")
        self.assertEqual(formula1.expression, "-Ka + Kb * Cl + T0")
        self.assertEqual(formula1.expr_type, wntr.reaction.model.RxnExprType.FORMULA)

    def test_WaterQualityReactionsModel_creation_specific_everything(self):
        rxn_model1 = wntr.reaction.model.WaterQualityReactionsModel()
        bulk1 = wntr.reaction.model.BulkSpecies("Cl", "mg")
        wall1 = wntr.reaction.model.WallSpecies("ClOH", "mg", 0.01, 0.0001, note="Testing stuff")
        const1 = wntr.reaction.model.Constant("Kb", 0.482)
        param1 = wntr.reaction.model.Parameter("Ka", 0.482, note="foo")
        term1 = wntr.reaction.model.OtherTerm("T0", "-3.2 * Kb * Cl^2", note="bar")
        equil1 = wntr.reaction.model.EquilibriumDynamics(bulk1, wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")
        rate1 = wntr.reaction.model.RateDynamics(bulk1, wntr.reaction.model.RxnLocType.TANK, "-Ka + Kb * Cl + T0", note="Foo Bar")
        formula1 = wntr.reaction.model.FormulaDynamics(wall1, wntr.reaction.model.RxnLocType.PIPE, "-Ka + Kb * Cl + T0")

        bulk2 = rxn_model1.add_bulk_species("Cl", "mg")
        wall2 = rxn_model1.add_wall_species("ClOH", "mg", 0.01, 0.0001, note="Testing stuff")
        const2 = rxn_model1.add_constant_coeff("Kb", 0.482)
        param2 = rxn_model1.add_parameterized_coeff("Ka", 0.482, note="foo")
        term2 = rxn_model1.add_other_term("T0", "-3.2 * Kb * Cl^2", note="bar")
        equil2 = rxn_model1.add_pipe_reaction("Cl", "equil", "-Ka + Kb * Cl + T0")
        rate2 = rxn_model1.add_tank_reaction("Cl", wntr.reaction.model.RxnExprType.R, "-Ka + Kb * Cl + T0", note="Foo Bar")
        formula2 = rxn_model1.add_reaction("PIPE", "ClOH", "formula", "-Ka + Kb * Cl + T0")
        self.assertEqual(bulk1, bulk2)
        self.assertEqual(wall1, wall2)
        self.assertEqual(const1, const2)
        # self.assertEqual(param1, param2) # No good way to compare dicts inside
        self.assertEqual(term1, term2)
        # self.assertEqual(equil1, equil2)
        # self.assertEqual(rate1, rate2)
        # self.assertEqual(formula1, formula2)

    def test_WaterQualityReactionsModel_creation_generic_species_coeffs(self):
        bulk1 = wntr.reaction.model.BulkSpecies("Cl", "mg")
        wall1 = wntr.reaction.model.WallSpecies("ClOH", "mg", 0.01, 0.0001, note="Testing stuff")
        const1 = wntr.reaction.model.Constant("Kb", 0.482)
        param1 = wntr.reaction.model.Parameter("Ka", 0.482, note="foo")
        term1 = wntr.reaction.model.OtherTerm("T0", "-3.2 * Kb * Cl^2", note="bar")

        rxn_model2 = wntr.reaction.model.WaterQualityReactionsModel()

        self.assertRaises(ValueError, rxn_model2.add_species, wntr.reaction.model.RxnVarType.CONST, "Cl", "mg")
        self.assertRaises(TypeError, rxn_model2.add_coefficient, None, "Kb", 0.482)
        self.assertRaises(ValueError, rxn_model2.add_coefficient, "Wall", "Kb", 0.482)

        bulk3 = rxn_model2.add_species("BULK", "Cl", "mg")
        wall3 = rxn_model2.add_species(wntr.reaction.model.RxnVarType.WALL, "ClOH", "mg", 0.01, 0.0001, note="Testing stuff")
        const3 = rxn_model2.add_coefficient("Consolation", "Kb", 0.482)
        param3 = rxn_model2.add_coefficient(wntr.reaction.model.RxnVarType.P, "Ka", 0.482, note="foo")

        self.assertEqual(bulk3, bulk1)
        self.assertEqual(wall3, wall1)
        self.assertEqual(const3, const1)
        self.assertEqual(param3, param1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

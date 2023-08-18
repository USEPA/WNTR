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

        param1 = wntr.reaction.model.Constant('Ka', 0.482)
        symbol3 = sympy.symbols('Ka')
        self.assertEqual(param1.get_symbol(), symbol3)

        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')
        symbol4 = sympy.symbols('T0')
        self.assertEqual(term1.get_symbol(), symbol4)


    def test_RxnVariable_values(self):
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        self.assertEqual(species1.get_value(), species1.value)
        self.assertRaises(TypeError, species1.get_value, pipe='blah')
        const1 = wntr.reaction.model.Constant('Kb', 0.482, note='test')
        self.assertEqual(const1.get_value(), const1.value)
        test_pipe_dict = {'PIPE': 0.38}
        test_tank_dict = {'TANK': 222.23}
        param2 = wntr.reaction.model.Parameter('Kb', 0.482, note='test', pipe_values=test_pipe_dict, tank_values=test_tank_dict)
        self.assertEqual(param2.get_value(), param2.global_value)
        self.assertEqual(param2.get_value(pipe='PIPE'), test_pipe_dict['PIPE'])
        self.assertEqual(param2.get_value(pipe='FOO'), param2.global_value)
        self.assertEqual(param2.get_value(tank='TANK'), test_tank_dict['TANK'])
        self.assertRaises(ValueError, param2.get_value, pipe='PIPE', tank='TANK')


    def test_RxnVariable_string_functions(self):
        species1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        species2 = wntr.reaction.model.WallSpecies('Cl', 'mg', 0.01, 0.0001, note='Testing stuff')
        const1 = wntr.reaction.model.Constant('Kb', 0.482)
        param1 = wntr.reaction.model.Parameter('Ka', 0.482, note='foo')
        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')

        self.assertEqual(str(species1), 'Cl')
        self.assertEqual(species1.to_msx_string(), 'BULK Cl mg  ;')
        self.assertEqual(species2.to_msx_string(), 'WALL Cl mg 0.01 0.0001 ;Testing stuff')
        self.assertEqual(str(const1), 'Kb')
        self.assertEqual(str(param1), 'Ka')
        self.assertEqual(const1.to_msx_string(), 'CONSTANT Kb 0.482 ;')
        self.assertEqual(param1.to_msx_string(), 'PARAMETER Ka 0.482 ;foo')
        self.assertEqual(str(term1), 'T0')
        self.assertEqual(term1.to_msx_string(), 'T0 -3.2 * Kb * Cl^2 ;bar')

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

    def test_Parameter_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.Parameter, 'Re')
        self.assertRaises(ValueError, wntr.reaction.model.Parameter, 'Re', 2.48)
        param1 = wntr.reaction.model.Parameter('Kb', 0.482, note='test')
        self.assertEqual(param1.name, 'Kb')
        self.assertEqual(param1.global_value, 0.482)
        self.assertEqual(param1.value, param1.global_value)
        self.assertEqual(param1.coeff_type, wntr.reaction.model.VarType.Parameter)
        self.assertEqual(param1.note, 'test')
        test_pipe_dict = {'PIPE': 0.38}
        test_tank_dict = {'TANK': 222.23}
        param2 = wntr.reaction.model.Parameter('Kb', 0.482, note='test', pipe_values=test_pipe_dict, tank_values=test_tank_dict)
        self.assertDictEqual(param2.pipe_values, test_pipe_dict)
        self.assertDictEqual(param2.tank_values, test_tank_dict)

    def test_RxnTerm_creation(self):
        self.assertRaises(TypeError, wntr.reaction.model.RxnTerm, 'Re')
        self.assertRaises(ValueError, wntr.reaction.model.RxnTerm, 'Re', '1.0*Re')
        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')
        self.assertEqual(term1.name, 'T0')
        self.assertEqual(term1.expression, '-3.2 * Kb * Cl^2')
        self.assertEqual(term1.variable_type, wntr.reaction.model.VarType.Term)
        self.assertEqual(term1.note, 'bar')
        self.assertEqual(term1.value, term1.expression)

    def test_RxnExpression_direct_instantiation_exceptions(self):
        self.assertRaises(TypeError, wntr.reaction.model.RxnExpression, 'Cl', wntr.reaction.model.RxnLocation.Pipes)
        self.assertRaises(NotImplementedError, wntr.reaction.model.RxnExpression, 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        self.assertRaises(TypeError, wntr.reaction.model.RxnExpression, 'Cl')
        self.assertRaises(TypeError, wntr.reaction.model.RxnExpression, 'Cl', 39)
        self.assertRaises(TypeError, wntr.reaction.model.RxnExpression, 'Cl', 39, '-Ka + Kb * Cl + T0')
        
    def test_RxnExpression_strings(self):
        equil1 = wntr.reaction.model.Equilibrium( 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        rate1 = wntr.reaction.model.Rate( 'Cl', wntr.reaction.model.RxnLocation.Tanks, '-Ka + Kb * Cl + T0', note='Foo Bar')
        formula1 = wntr.reaction.model.Formula( 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        self.assertEqual(equil1.to_msx_string(), 'EQUIL Cl -Ka + Kb * Cl + T0 ;')
        self.assertEqual(rate1.to_msx_string(), 'RATE Cl -Ka + Kb * Cl + T0 ;Foo Bar')
        self.assertEqual(formula1.to_msx_string(), 'FORMULA Cl -Ka + Kb * Cl + T0 ;')

    def test_Equilibrium_creation(self):
        equil1 = wntr.reaction.model.Equilibrium( 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        self.assertEqual(equil1.species, 'Cl')
        self.assertEqual(equil1.expression, '-Ka + Kb * Cl + T0')
        self.assertEqual(equil1.expression_type, wntr.reaction.model.ExprType.Equil)

    def test_Rate_creation(self):
        rate1 = wntr.reaction.model.Rate( 'Cl', wntr.reaction.model.RxnLocation.Tanks, '-Ka + Kb * Cl + T0', note='Foo Bar')
        self.assertEqual(rate1.species, 'Cl')
        self.assertEqual(rate1.expression, '-Ka + Kb * Cl + T0')
        self.assertEqual(rate1.expression_type, wntr.reaction.model.ExprType.Rate)
        self.assertEqual(rate1.note, 'Foo Bar')

    def test_Formula_creation(self):
        formula1 = wntr.reaction.model.Formula( 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        self.assertEqual(formula1.species, 'Cl')
        self.assertEqual(formula1.expression, '-Ka + Kb * Cl + T0')
        self.assertEqual(formula1.expression_type, wntr.reaction.model.ExprType.Formula)
    
    def test_WaterQualityReactionsModel_creation_specific_everything(self):
        rxn_model1 = wntr.reaction.model.WaterQualityReactionsModel()
        bulk1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        wall1 = wntr.reaction.model.WallSpecies('ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const1 = wntr.reaction.model.Constant('Kb', 0.482)
        param1 = wntr.reaction.model.Parameter('Ka', 0.482, note='foo')
        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')
        equil1 = wntr.reaction.model.Equilibrium( 'Cl', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')
        rate1 = wntr.reaction.model.Rate( 'Cl', wntr.reaction.model.RxnLocation.Tanks, '-Ka + Kb * Cl + T0', note='Foo Bar')
        formula1 = wntr.reaction.model.Formula( 'ClOH', wntr.reaction.model.RxnLocation.Pipes, '-Ka + Kb * Cl + T0')

        bulk2 = rxn_model1.add_bulk_species('Cl', 'mg')
        wall2 = rxn_model1.add_wall_species('ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const2 = rxn_model1.add_constant('Kb', 0.482)
        param2 = rxn_model1.add_parameter('Ka', 0.482, note='foo')
        term2 = rxn_model1.add_term('T0', '-3.2 * Kb * Cl^2', note='bar')
        equil2 = rxn_model1.add_pipe_reaction('equil', 'Cl', '-Ka + Kb * Cl + T0')
        rate2 = rxn_model1.add_tank_reaction(wntr.reaction.model.ExprType.Rate, 'Cl', '-Ka + Kb * Cl + T0', note='Foo Bar')
        formula2 = rxn_model1.add_reaction('pipes', 'formula', 'ClOH', '-Ka + Kb * Cl + T0')
        self.assertEqual(bulk1, bulk2)
        self.assertEqual(wall1, wall2)
        self.assertEqual(const1, const2)
        self.assertEqual(param1, param2)
        self.assertEqual(term1, term2)
        self.assertEqual(equil1, equil2)
        self.assertEqual(rate1, rate2)
        self.assertEqual(formula1, formula2)

    def test_WaterQualityReactionsModel_creation_generic_species_coeffs(self):
        bulk1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        wall1 = wntr.reaction.model.WallSpecies('ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const1 = wntr.reaction.model.Constant('Kb', 0.482)
        param1 = wntr.reaction.model.Parameter('Ka', 0.482, note='foo')
        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')

        rxn_model2 = wntr.reaction.model.WaterQualityReactionsModel()

        self.assertRaises(ValueError, rxn_model2.add_species, wntr.reaction.model.VarType.Species, 'Cl', 'mg')
        self.assertRaises(TypeError, rxn_model2.add_coefficient, None, 'Kb', 0.482)
        self.assertRaises(ValueError, rxn_model2.add_coefficient, 'Wall', 'Kb', 0.482)

        bulk3 = rxn_model2.add_species('Bulk', 'Cl', 'mg')
        wall3 = rxn_model2.add_species(wntr.reaction.model.VarType.Wall, 'ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const3 = rxn_model2.add_coefficient('Consolation', 'Kb', 0.482)
        param3 = rxn_model2.add_coefficient(wntr.reaction.model.VarType.P, 'Ka', 0.482, note='foo')

        self.assertEqual(bulk3, bulk1)
        self.assertEqual(wall3, wall1)
        self.assertEqual(const3, const1)
        self.assertEqual(param3, param1)

    def test_WaterQualityReactionsModel_creation_generic_variables_reactions(self):
        bulk1 = wntr.reaction.model.BulkSpecies('Cl', 'mg')
        wall1 = wntr.reaction.model.WallSpecies('ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const1 = wntr.reaction.model.Constant('Kb', 0.482)
        param1 = wntr.reaction.model.Parameter('Ka', 0.482, note='foo')
        term1 = wntr.reaction.model.RxnTerm('T0', '-3.2 * Kb * Cl^2', note='bar')

        rxn_model2 = wntr.reaction.model.WaterQualityReactionsModel()

        self.assertRaises(ValueError, rxn_model2.add_variable, wntr.reaction.model.VarType.Species, 'Cl', 'mg')
        self.assertRaises(ValueError, rxn_model2.add_variable, None, 'Kb', 0.482)

        bulk3 = rxn_model2.add_variable('Bulk', 'Cl', 'mg')
        wall3 = rxn_model2.add_variable(wntr.reaction.model.VarType.Wall, 'ClOH', 'mg', 0.01, 0.0001, note='Testing stuff')
        const3 = rxn_model2.add_variable('Consolation', 'Kb', 0.482)
        param3 = rxn_model2.add_variable(wntr.reaction.model.VarType.P, 'Ka', 0.482, note='foo')
        term3 = rxn_model2.add_variable('tErM', 'T0', '-3.2 * Kb * Cl^2', note='bar')

        self.assertEqual(bulk3, bulk1)
        self.assertEqual(wall3, wall1)
        self.assertEqual(const3, const1)
        self.assertEqual(param3, param1)
        self.assertEqual(term3, term1)

if __name__ == "__main__":
    unittest.main(verbosity=2)

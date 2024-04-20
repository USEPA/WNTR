import unittest
from os.path import abspath, dirname, join, exists

import wntr.epanet.exceptions

testdir = dirname(abspath(__file__))
datadir = join(testdir, "networks_for_testing")


class TestEpanetExceptions(unittest.TestCase):
    
    def test_epanet_exception(self):
        try:
            raise wntr.epanet.exceptions.EpanetException(213, '13:00:00 pm', 'Cannot specify am/pm for times greater than 12:00:00')
        except Exception as e:
            self.assertTupleEqual(e.args, ("(Error 213) invalid option value '13:00:00 pm' ['Cannot specify am/pm for times greater than 12:00:00']",))
        try:
            raise wntr.epanet.exceptions.EpanetException(999)
        except Exception as e:
            self.assertTupleEqual(e.args, ('(Error 999) unknown error',))
        try:
            raise wntr.epanet.exceptions.EpanetException(108)
        except Exception as e:
            self.assertTupleEqual(e.args, ('(Error 108) cannot use external file while hydraulics solver is active',))

    def test_epanet_syntax_error(self):
        try:
            raise wntr.epanet.exceptions.ENSyntaxError(223, line_num=38, line='I AM A SYNTAX ERROR')
        except SyntaxError as e:
            self.assertTupleEqual(e.args, ('(Error 223) not enough nodes in network, at line 38:\n   I AM A SYNTAX ERROR',))

    def test_epanet_key_error(self):
        try:
            raise wntr.epanet.exceptions.ENKeyError(206, 'NotACurve')
        except KeyError as e:
            self.assertTupleEqual(e.args, ("(Error 206) undefined curve, 'NotACurve'",))

    def test_epanet_value_error(self):
        try:
            raise wntr.epanet.exceptions.ENValueError(213, 423.0e28)
        except ValueError as e:
            self.assertTupleEqual(e.args, ('(Error 213) invalid option value 4.23e+30',))

    def test_broken_time_string(self):
        f = wntr.epanet.io.InpFile()
        inp_file = join(datadir, "bad_times.inp")
        try:
            f.read(inp_file)
        except Exception as e:
            self.assertIsInstance(e.__cause__, wntr.epanet.exceptions.ENValueError)
        else:
            self.fail('Failed to catch expected errors in bad_times.inp')

    def test_broken_syntax(self):
        f = wntr.epanet.io.InpFile()
        inp_file = join(datadir, "bad_syntax.inp")
        try:
            f.read(inp_file)
        except Exception as e:
            self.assertIsInstance(e, wntr.epanet.exceptions.ENSyntaxError)
        else:
            self.fail('Failed to catch expected errors in bad_syntax.inp')

    def test_bad_values(self):
        f = wntr.epanet.io.InpFile()
        inp_file = join(datadir, "bad_values.inp")
        try:
            f.read(inp_file)
        except Exception as e:
            self.assertIsInstance(e.__cause__, wntr.epanet.exceptions.ENKeyError)
        else:
            self.fail('Failed to catch expected errors in bad_values.inp')

if __name__ == "__main__":
    unittest.main()

import unittest
from os.path import abspath, dirname, join, exists

import wntr.epanet.exceptions

testdir = dirname(abspath(__file__))
datadir = join(testdir, "..", "..", "examples", "networks")


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



if __name__ == "__main__":
    unittest.main()

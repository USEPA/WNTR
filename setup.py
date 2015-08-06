from setuptools import setup, find_packages
from distutils.core import Extension

setup(name='wntr',
    version='0.1',
    description='Water iNfrastucture Tool for Resilience',
    url='https://software.sandia.gov/git/resilience',
    license='Revised BSD',
    packages=find_packages(),
    data_files=[('my_data', ['epanetlib/tests/networks_for_testing/Net1.inp']), 
                ('epanetlib/pyepanet/data/Linux',['epanetlib/pyepanet/data/Linux/libepanet2_amd64.so']),
                ('epanetlib/pyepanet/data/Darwin',['epanetlib/pyepanet/data/Darwin/libepanet.dylib']),
                ('epanetlib/pyepanet/data/Windows',['epanetlib/pyepanet/data/Windows/EN2setup.exe', 'epanetlib/pyepanet/data/Windows/epanet2.bas','epanetlib/pyepanet/data/Windows/epanet2.def','epanetlib/pyepanet/data/Windows/epanet2.dll','epanetlib/pyepanet/data/Windows/epanet2.lib','epanetlib/pyepanet/data/Windows/epanet2.pas'])],
    zip_safe=False)


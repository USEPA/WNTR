from setuptools import setup, find_packages

setup(name='epanetlib',
    version='0.1',
    description='Water Network Tool for Resilience',
    url='https://software.sandia.gov/git/resilience',
    license='Revised BSD',
    packages=find_packages(),
    package_data={
        'epanetlib/pyepanet/data/Windows': ['EN2setup.exe'],
        },             
    data_files=[('my_data', ['epanetlib/tests/networks_for_testing/Net1.inp'])],
    zip_safe=False)
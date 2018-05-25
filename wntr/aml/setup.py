from setuptools import setup, find_packages
from setuptools.extension import Extension
import shutil
import numpy
import os
from distutils.spawn import find_executable

try:
    numpy_include = numpy.get_include()
except AttributeError:
    numpy_include = numpy.get_numpy_include()

print('********************************')
print(numpy_include)
print('********************************')

ipopt_executable = find_executable('ipopt')

if ipopt_executable is None:
    raise RuntimeError('Ipopt not in path. Installation unsuccessful')
else:
    print('Ipopt found in {}'.format(ipopt_executable))

ipopt_bin = os.path.dirname(ipopt_executable)
ipopt_base = os.path.dirname(ipopt_bin)
ipopt_include = os.path.join(ipopt_base, 'include', 'coin')
ipopt_include_third_party = os.path.join(ipopt_include, 'ThirdParty')
ipopt_lib = os.path.join(ipopt_base, 'lib')

# inplace extension module
project_dir = os.path.dirname(os.path.abspath(__file__))
src_files = os.path.join(project_dir, 'aml')
expression_cxx = os.path.join(src_files, 'expression.cpp')
component_cxx = os.path.join(src_files, 'component.cpp')
wntr_model_cxx = os.path.join(src_files, 'wntr_model.cpp')
aml_core_i = os.path.join(src_files, 'aml_core.i')
ipopt_model_i = os.path.join(src_files, 'ipopt_model.i')
ipopt_model_cxx = os.path.join(src_files, 'ipopt_model.cpp')
aml_tnlp_cxx = os.path.join(src_files, 'aml_tnlp.cpp')

extension_modules = list()

aml_core_ext = Extension("aml._aml_core",
                           sources=[aml_core_i, expression_cxx, component_cxx, wntr_model_cxx],
                           language="c++",
                           extra_compile_args=["-std=c++11"],
                           include_dirs=[numpy_include, src_files],
                           library_dirs=[],
                           libraries=[],
                           swig_opts=['-c++'])
extension_modules.append(aml_core_ext)

ipopt_model_ext = Extension("aml._ipopt_model",
                            sources=[ipopt_model_i, ipopt_model_cxx, aml_tnlp_cxx],
                            language="c++",
                            extra_compile_args=["-std=c++11"],  # , "-stdlib=libc++"],
                            include_dirs=[numpy_include, src_files, ipopt_include],
                            library_dirs=[ipopt_lib],
                            libraries=[os.path.join(ipopt_lib, 'ipopt')],
                            swig_opts=['-c++'])
extension_modules.append(ipopt_model_ext)

for i in extension_modules:
    print(i)

setup_kwargs = {
    'requires': [],
    'scripts': [],
}

setup(name="aml",
      description="Python AML and AD",
      author="Michael Bynumm",
      version="0.0",
      packages=['aml'],
      ext_modules=extension_modules,
      **setup_kwargs
    )

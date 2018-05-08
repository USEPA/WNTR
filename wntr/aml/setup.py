from setuptools import setup, find_packages
from setuptools.extension import Extension
import shutil
import numpy
import os

try:
    numpy_include = numpy.get_include()
except AttributeError:
    numpy_include = numpy.get_numpy_include()

ipopt_executable = shutil.which('ipopt')

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
src_files = os.path.join(project_dir, 'ipaml')
swig_expression_i = os.path.join(src_files, 'expression.i')
expression_cxx = os.path.join(src_files, 'expression.cpp')
swig_ipopt_model_i = os.path.join(src_files, 'ipopt_model.i')
ipopt_model_cxx = os.path.join(src_files, 'ipopt_model.cpp')
aml_tnlp_cxx = os.path.join(src_files, 'aml_tnlp.cpp')

print(ipopt_base)
print(ipopt_include)
print(ipopt_include_third_party)
print(ipopt_lib)
print(project_dir)
print(swig_expression_i)
print(expression_cxx)
print(swig_ipopt_model_i)
print(ipopt_model_cxx)
print(aml_tnlp_cxx)

extension_modules = list()

expression_ext = Extension("ipaml._expression",
                           sources=[swig_expression_i, expression_cxx],
                           language="c++",
                           extra_compile_args=["-std=c++11"],  # , "-stdlib=libc++"],
                           include_dirs=[numpy_include, src_files, ipopt_include],
                           library_dirs=[ipopt_lib],
                           libraries=[os.path.join(ipopt_lib, 'ipopt')],
                           swig_opts=['-c++'])

extension_modules.append(expression_ext)

ipopt_model_ext = Extension("ipaml._ipopt_model",
                            sources=[swig_ipopt_model_i, ipopt_model_cxx, aml_tnlp_cxx],
                            language="c++",
                            extra_compile_args=["-std=c++11"],  # , "-stdlib=libc++"],
                            include_dirs=[numpy_include, src_files, ipopt_include],
                            library_dirs=[ipopt_lib],
                            libraries=[os.path.join(ipopt_lib, 'ipopt')],
                            swig_opts=['-c++'])

extension_modules.append(ipopt_model_ext)

for i in extension_modules:
    print(type(i))

setup_kwargs = {
    'requires': [],
    'scripts': [],
}

setup(name="ipaml",
      description="Python AML and AD",
      author="Michael Bynumm",
      version="0.0",
      packages=['ipaml'],
      ext_modules=extension_modules,
      **setup_kwargs
    )

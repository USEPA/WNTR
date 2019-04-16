%module evaluator
%include exception.i

%{
  #define SWIG_FILE_WITH_INIT
  #include "evaluator.hpp"
%}

%exception
{
  try
    {
      $action
    }
  catch (StructureException &e)
    {
      std::string s("Evaluator error: "), s2(e.what());
      s = s + s2;
      SWIG_exception(SWIG_RuntimeError, s.c_str());
    }
  catch (...)
    {
      SWIG_exception(SWIG_RuntimeError, "unkown exception");
    }
}

%include "numpy.i"
%init %{
  import_array();
%}

%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *array_out, int array_length_out)}
%apply (double *ARGOUT_ARRAY1, int DIM1) {(double *values_array_out, int values_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *col_ndx_array_out, int col_ndx_array_length_out)}
%apply (int *ARGOUT_ARRAY1, int DIM1) {(int *row_nnz_array_out, int row_nnz_array_length_out)}
%apply (double *IN_ARRAY1, int DIM1) {(double *array_in, int array_length_in)}

%include "evaluator.hpp"

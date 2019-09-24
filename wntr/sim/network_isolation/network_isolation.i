%module network_isolation
%{
  #define SWIG_FILE_WITH_INIT
  #include "network_isolation.hpp"
%}

%include "numpy.i"
%init %{
  import_array();
%}

%apply (long *INPLACE_ARRAY1, int DIM1) {(long *node_indicator, int num_nodes)}
%apply (long *IN_ARRAY1, int DIM1) {(long *sources, int source_length)}
%apply (long *IN_ARRAY1, int DIM1) {(long *indptr, int indptr_length)}
%apply (long *IN_ARRAY1, int DIM1) {(long *indices, int indices_length)}
%apply (long *IN_ARRAY1, int DIM1) {(long *data, int data_length)}
%apply (long *IN_ARRAY1, int DIM1) {(long *num_connections, int num_connections_length)}

%include "network_isolation.hpp"

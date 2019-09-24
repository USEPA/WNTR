#include <set>
#include <climits>
#include <stdexcept>

int get_long_size();

void check_for_isolated_junctions(long *sources, int source_length, long *node_indicator, int num_nodes, long *indptr, int indptr_length, long *indices, int indices_length, long *data, int data_length, long *num_connections, int num_connections_length);

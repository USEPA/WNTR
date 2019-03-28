#include "network_isolation.hpp"


int get_long_size()
{
  if (CHAR_BIT != 8)
    {
      throw std::runtime_error("Expected CHAR_BIT to be 8. Please report this to the WNTR developers.");
    }
  return (int) sizeof(long);
}


void check_for_isolated_junctions(long *sources, int source_length, long *node_indicator, int num_nodes, long *indptr, int indptr_length, long *indices, int indices_length, long *data, int data_length, long *num_connections, int num_connections_length)
{
  int source_id;
  int node_being_explored;
  int ndx;
  int number_of_connections;
  int val;
  int col;

  for (int source_cntr = 0; source_cntr < source_length; ++ source_cntr)
    {
      source_id = sources[source_cntr];
      if (node_indicator[source_id] == 1)
        {
	  node_indicator[source_id] = 0;
	  std::set<int> nodes_to_explore;
	  nodes_to_explore.insert(source_id);

	  while (!nodes_to_explore.empty())
            {
	      std::set<int>::iterator nodes_to_explore_iter = nodes_to_explore.end();
	      --nodes_to_explore_iter;
	      node_being_explored = *nodes_to_explore_iter;
	      nodes_to_explore.erase(nodes_to_explore_iter);
	      ndx = indptr[node_being_explored];
	      number_of_connections = num_connections[node_being_explored];
	      for (int i = 0; i < number_of_connections; ++i)
                {
		  val = data[ndx + i];
		  if (val == 1)
                    {
		      col = indices[ndx + i];
		      if (node_indicator[col] == 1)
                        {
			  node_indicator[col] = 0;
			  nodes_to_explore.insert(col);
                        }
                    }
                }
            }
        }
    }
}

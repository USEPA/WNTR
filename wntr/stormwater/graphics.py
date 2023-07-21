import networkx as nx
import matplotlib.pylab as plt

def plot_network(
    swn,
    node_attribute=None,
    link_attribute=None,
    title=None,
    node_size=20,
    node_range=[None, None],
    node_alpha=1,
    node_cmap=None,
    node_labels=False,
    link_width=1,
    link_range=[None, None],
    link_alpha=1,
    link_cmap=None,
    link_labels=False,
    add_colorbar=True,
    node_colorbar_label="Node",
    link_colorbar_label="Link",
    directed=False,
    ax=None,
    filename=None,
    inpdata=None,
):

    if ax is None:  # create a new figure
        plt.figure(facecolor="w", edgecolor="k")
        ax = plt.gca()

    # Graph
    G = swn.to_graph()
    if not directed:
        G = G.to_undirected()

    # Position
    pos = nx.get_node_attributes(G, "coords")
    pos = dict((k, (v[0][0], v[0][1])) for k,v in pos.items())
    if len(pos) == 0:
        pos = None

    # Define node properties
    add_node_colorbar = add_colorbar
    if node_attribute is not None:

        if isinstance(node_attribute, list):
            if node_cmap is None:
                node_cmap = ["red", "red"]
            add_node_colorbar = False

        if node_cmap is None:
            node_cmap = plt.get_cmap("Spectral_r")
        elif isinstance(node_cmap, list):
            if len(node_cmap) == 1:
                node_cmap = node_cmap * 2
            node_cmap = custom_colormap(len(node_cmap), node_cmap)

        node_attribute = dict(node_attribute)
        nodelist, nodecolor = zip(*node_attribute.items())

    else:
        nodelist = None
        nodecolor = "k"

    add_link_colorbar = add_colorbar
    if link_attribute is not None:

        if isinstance(link_attribute, list):
            if link_cmap is None:
                link_cmap = ["red", "red"]
            add_link_colorbar = False

        if link_cmap is None:
            link_cmap = plt.get_cmap("Spectral_r")
        elif isinstance(link_cmap, list):
            if len(link_cmap) == 1:
                link_cmap = link_cmap * 2
            link_cmap = custom_colormap(len(link_cmap), link_cmap)

        link_attribute = dict(link_attribute)

        # Replace link_attribute dictionary defined as
        # {link_name: attr} with {(start_node, end_node, link_name): attr}
        attr = {}
        edge_tuples = list(G.edges(keys=True))
        for edge_tuple in list(G.edges(keys=True)):
            edge_name = edge_tuple[2]
            try:
                value = link_attribute[edge_name]
                attr[edge_tuple] = value
            except:
                pass
        link_attribute = attr

        linklist, linkcolor = zip(*link_attribute.items())
    else:
        linklist = None
        linkcolor = "k"

    if title is not None:
        ax.set_title(title)
    
    for subcatch in swn.subcatchments['geometry']:
        ax.plot(*subcatch.boundary.xy, c='gray', linewidth=0.5)

    edge_background = nx.draw_networkx_edges(G, pos, edge_color="grey", width=0.5, ax=ax)

    nodes = nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=nodelist,
        node_color=nodecolor,
        node_size=node_size,
        alpha=node_alpha,
        cmap=node_cmap,
        vmin=node_range[0],
        vmax=node_range[1],
        linewidths=0,
        ax=ax,
    )
    edges = nx.draw_networkx_edges(
        G,
        pos,
        edgelist=linklist,
        edge_color=linkcolor,
        width=link_width,
        alpha=link_alpha,
        edge_cmap=link_cmap,
        edge_vmin=link_range[0],
        edge_vmax=link_range[1],
        ax=ax,
    )

    if add_node_colorbar and node_attribute:
        clb = plt.colorbar(nodes, shrink=0.5, pad=0, ax=ax)
        clb.ax.set_title(node_colorbar_label, fontsize=10)
    if add_link_colorbar and link_attribute:
        if directed:
            vmin = min(map(abs, link_attribute.values()))
            vmax = max(map(abs, link_attribute.values()))
            sm = plt.cm.ScalarMappable(cmap=link_cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
            sm.set_array([])
            clb = plt.colorbar(sm, shrink=0.5, pad=0.05, ax=ax)
        else:
            clb = plt.colorbar(edges, shrink=0.5, pad=0.05, ax=ax)
        clb.ax.set_title(link_colorbar_label, fontsize=10)

    ax.axis("off")

    if filename:
        plt.savefig(filename)

    return ax

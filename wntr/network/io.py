# coding: utf-8

"""
The wntr.network.elements module includes elements of a water network model, 
including junction, tank, reservoir, pipe, pump, valve, pattern, timeseries, 
demands, curves, and sources.

.. rubric:: Contents

.. autosummary::

    to_dict
    from_dict
    write_json
    read_json
    write_inpfile
    read_inpfile

"""
import logging
import json

import wntr.epanet
from wntr.epanet.util import FlowUnits
import wntr.network.model

logger = logging.getLogger(__name__)


def to_dict(wn) -> dict:
    """Dictionary representation of the WaterNetworkModel.
    
    Parameters
    ----------
    wn : WaterNetworkModel
        the water network model to convert to a dictionary

    Returns
    -------
    dict
        dictionary representation of the water network model
    """
    from wntr import __version__

    controls = list()
    for k, c in wn._controls.items():
        cc = c.to_dict()
        if "name" in cc.keys() and not cc["name"]:
            cc["name"] = k
        controls.append(cc)
    d = dict(
        version="wntr-{}".format(__version__),
        comment="WaterNetworkModel - all values given in SI units",
        name=wn.name,
        options=wn._options.to_dict(),
        curves=wn._curve_reg.to_list(),
        patterns=wn._pattern_reg.to_list(),
        nodes=wn._node_reg.to_list(),
        links=wn._link_reg.to_list(),
        sources=wn._sources.to_list(),
        controls=controls,
    )
    return d


def from_dict(
    d: dict, append=None,
):
    """
    Create or append a water network model object from a dictionary.

    Parameters
    ----------
    d : dict
        dictionary representation of the water network model
    append : WaterNetworkModel, optional
        an existing water network model to append results to

    Returns
    -------
    WaterNetworkModel
        a new water network model or the appended existing model
    """
    from wntr.epanet.io import _read_control_line, _EpanetRule

    keys = [
        "version",
        "comment",
        "name",
        "options",
        "curves",
        "patterns",
        "nodes",
        "links",
        "sources",
        "controls",
    ]
    for key in keys:
        if key not in d.keys():
            logger.warning("Dictionary model missing key '{}'".format(key))
    if append is None:
        wn = wntr.network.model.WaterNetworkModel()
    else:
        wn = append
    if "name" in d:
        wn.name = d["name"]
    if "options" in d:
        wn.options.__init__(**d["options"])
    if "curves" in d:
        for curve in d["curves"]:
            wn.add_curve(
                name=curve["name"], curve_type=curve["curve_type"], xy_tuples_list=curve["points"]
            )
    if "patterns" in d:
        for pattern in d["patterns"]:
            wn.add_pattern(name=pattern["name"], pattern=pattern["multipliers"])
    if "nodes" in d:
        for node in d["nodes"]:
            name = node["name"]
            if node["node_type"] == "Junction":
                dl = node.setdefault("demand_timeseries_list")
                if dl is not None and len(dl) > 0:
                    base_demand = dl[0].setdefault("base_val", 0.0)
                    pattern_name = dl[0].setdefault("pattern_name")
                    category = dl[0].setdefault("category")
                else:
                    base_demand = 0.0
                    pattern_name = None
                    category = None
                wn.add_junction(
                    name=name,
                    base_demand=base_demand,
                    demand_pattern=pattern_name,
                    elevation=node.setdefault("elevation"),
                    coordinates=node.setdefault("coordinates", list()),
                    demand_category=category,
                )
                j = wn.get_node(name)
                j.emitter_coefficient = node.setdefault("emitter_coefficient")
                j.initial_quality = node.setdefault("initial_quality")
                j.minimum_pressure = node.setdefault("minimum_pressure")
                j.pressure_exponent = node.setdefault("pressure_exponent")
                j.required_pressure = node.setdefault("required_pressure")
                j.tag = node.setdefault("tag")
                if dl is not None and len(dl) > 1:
                    for i in range(1, len(dl)):
                        base_val = dl[i].setdefault("base_val", 0.0)
                        pattern_name = dl[i].setdefault("pattern_name")
                        category = dl[i].setdefault("category")
                        j.add_demand(base_val, pattern_name, category)
            elif node["node_type"] == "Tank":
                coordinates = node.setdefault("coordinates")

                wn.add_tank(
                    name,
                    elevation=node.setdefault("elevation"),
                    init_level=node.setdefault("init_level", node.setdefault("min_level", 0)),
                    max_level=node.setdefault("max_level", node.setdefault("min_level", 0) + 10),
                    diameter=node.setdefault("diameter", 0),
                    min_level=node.setdefault("min_level", 0),
                    vol_curve=node.setdefault("vol_curve_name"),
                    overflow=node.setdefault("overflow", False),
                    coordinates=coordinates,
                )
                t = wn.get_node(name)
                t.initial_quality = node.setdefault("initial_quality", 0.0)
                if node.setdefault("mixing_fraction"):
                    t.mixing_fraction = node.setdefault("mixing_fraction")
                if node.setdefault("mixing_model"):
                    t.mixing_model = node.setdefault("mixing_model")
                t.tag = node.setdefault("tag")
                t.bulk_coeff = node.setdefault("bulk_coeff")
            elif node["node_type"] == "Reservoir":
                wn.add_reservoir(
                    name,
                    base_head=node.setdefault("base_head"),
                    head_pattern=node.setdefault("head_pattern_name"),
                    coordinates=node.setdefault("coordinates"),
                )
                r = wn.get_node(name)
                r.initial_quality = node.setdefault("initial_quality", 0.0)
                r.tag = node.setdefault("tag")
            else:
                raise ValueError("Illegal node type '{}'".format(node["node_type"]))
    if "links" in d:
        for link in d["links"]:
            name = link["name"]
            if link["link_type"] == "Pipe":
                wn.add_pipe(
                    name,
                    link["start_node_name"],
                    end_node_name=link["end_node_name"],
                    length=link.setdefault("length", 304.8),
                    diameter=link.setdefault("diameter", 0.3048),
                    roughness=link.setdefault("roughness", 100.0),
                    minor_loss=link.setdefault("minor_loss", 0.0),
                    initial_status=link.setdefault("initial_status", "OPEN"),
                    check_valve=link.setdefault("check_valve", False),
                )
                p = wn.get_link(name)
                p.bulk_coeff = link.setdefault("bulk_coeff")
                p.tag = link.setdefault("tag")
                p.vertices = link.setdefault("vertices", list())
                p.wall_coeff = link.setdefault("wall_coeff")
            elif link["link_type"] == "Pump":
                pump_type = link.setdefault("pump_type", "POWER")
                wn.add_pump(
                    name,
                    link["start_node_name"],
                    link["end_node_name"],
                    pump_type=pump_type,
                    pump_parameter=link.setdefault("power")
                    if pump_type.lower() == "power"
                    else link.setdefault("pump_curve_name"),
                    speed=link.setdefault("base_speed", 1.0),
                    pattern=link.setdefault("speed_pattern_name"),
                    initial_status=link.setdefault("initial_status", "OPEN"),
                )
                p = wn.get_link(name)
                p.efficiency = link.setdefault("efficiency")
                p.energy_pattern = link.setdefault("energy_pattern")
                p.energy_price = link.setdefault("energy_price")
                p.initial_setting = link.setdefault("initial_setting")
                p.tag = link.setdefault("tag")
                p.vertices = link.setdefault("vertices", list())
            elif link["link_type"] == "Valve":
                valve_type = link["valve_type"]
                wn.add_valve(
                    name,
                    link["start_node_name"],
                    link["end_node_name"],
                    diameter=link.setdefault("diameter", 0.3048),
                    valve_type=valve_type,
                    minor_loss=link.setdefault("minor_loss", 0),
                    initial_setting=link.setdefault("initial_setting", 0),
                    initial_status=link.setdefault("initial_status", "ACTIVE"),
                )
                v = wn.get_link(name)
                if valve_type.lower() == "gpv":
                    v.headloss_curve_name = link.setdefault("headloss_curve_name")
            else:
                raise ValueError("Illegal link type '{}'".format(link["link_type"]))
    if "sources" in d:
        for source in d["sources"]:
            wn.add_source(
                source["name"],
                node_name=source["node_name"],
                source_type=source["source_type"],
                quality=source["strength"],
                pattern=source["pattern"],
            )
    if "controls" in d:  # TODO: FIXME: FINISH
        control_count = 0
        for control in d["controls"]:
            ctrl_type = control["type"]
            if ctrl_type.lower() == "simple":
                control_count += 1
                control_name = "control " + str(control_count)
                ta = control["then_actions"][0].split()
                tstring = " ".join([ta[0], ta[1], ta[4]])
                cond = control["condition"].split()
                if cond[0].lower() == "system":
                    cstr = " ".join(["AT", cond[1], cond[3], cond[4] if len(cond) > 4 else ""])
                else:
                    cstr = " ".join(["IF", cond[0], cond[1], cond[3], cond[4]])
                ctrl = _read_control_line(tstring + " " + cstr, wn, FlowUnits.SI, control_name)
                wn.add_control(control_name, ctrl)
            elif ctrl_type.lower() == "rule":
                ctrllst = ["RULE"]
                control_name = control["name"]
                ctrllst.append(control["name"])
                ctrllst.append("IF")
                ctrllst.append(control["condition"])
                thenact = " AND ".join(control["then_actions"])
                ctrllst.append("THEN")
                ctrllst.append(thenact)
                if "else_actions" in control and control["else_actions"]:
                    ctrllst.append("ELSE")
                    ctrllst.append(" AND ".join(control["else_actions"]))
                ctrllst.append("PRIORITY")
                ctrllst.append(str(control["priority"]))
                ctrlstring = " ".join(ctrllst)
                c = _EpanetRule.parse_rules_lines([ctrlstring])
                wn.add_control(control_name, c[0].generate_control(wn))
            else:
                raise ValueError("Illegal control type '{}'".format(ctrl_type))
    return wn


def write_json(
    wn, path_or_buf, **kw_json,
):
    """
    Write the WaterNetworkModel to a JSON file

    Parameters
    ----------
    path_or_buf : str or IO stream
        Name of the file or file pointer
    kw_json : keyword arguments
        arguments to pass directly to `json.dump`
    """
    if isinstance(path_or_buf, str):
        with open(path_or_buf, "w") as fout:
            json.dump(to_dict(wn), fout, **kw_json)
    else:
        json.dump(to_dict(wn), path_or_buf, **kw_json)


def read_json(
    path_or_buf, append=None, **kw_json,
):
    """
    Create a WaterNetworkModel from a JSON file.

    Parameters
    ----------
    f : str
        Name of the file or file pointer
    kw_json : keyword arguments
        keyword arguments to pass to `json.load`

    Returns
    -------
    WaterNetworkModel
    """
    if isinstance(path_or_buf, str):
        with open(path_or_buf, "r") as fin:
            d = json.load(fin, **kw_json)
    else:
        d = json.load(path_or_buf, **kw_json)
    return from_dict(d, append)


def write_inpfile(
    wn, filename: str, units=None, version: float = 2.2, force_coordinates: bool = False,
):
    """
    Writes the current water network model to an EPANET INP file

    .. note::

        By default, WNTR now uses EPANET version 2.2 for the EPANET simulator engine. Thus,
        The WaterNetworkModel will also write an EPANET 2.2 formatted INP file by default as well.
        Because the PDD analysis options will break EPANET 2.0, the ``version`` option will allow
        the user to force EPANET 2.0 compatibility at the expense of pressured-dependent analysis 
        options being turned off.


    Parameters
    ----------
    wn : WaterNetworkModel
        model object to write INP file for

    filename : string
        Name of the inp file.

    units : str, int or FlowUnits
        Name of the units being written to the inp file.

    version : float, {2.0, **2.2**}
        Optionally specify forcing EPANET 2.0 compatibility.

    force_coordinates : bool
        This only applies if `self.options.graphics.map_filename` is not `None`,
        and will force the COORDINATES section to be written even if a MAP file is
        provided. False by default, but coordinates **are** written by default since
        the MAP file is `None` by default.

    """
    if wn._inpfile is None:
        logger.warning("Writing a minimal INP file without saved non-WNTR options (energy, etc.)")
        wn._inpfile = wntr.epanet.InpFile()
    if units is None:
        units = wn._options.hydraulic.inpfile_units
    wn._inpfile.write(
        filename, wn, units=units, version=version, force_coordinates=force_coordinates
    )


def read_inpfile(
    filename, append=None,
):
    """
    Defines water network model components from an EPANET INP file

    Parameters
    ----------
    filename : string
        Name of the INP file.

    """
    inpfile = wntr.epanet.InpFile()
    wn = inpfile.read(filename, wn=append)
    wn._inpfile = inpfile
    return wn

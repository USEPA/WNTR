"""
The wntr.msx.io module includes functions that convert the MSX reaction
model to other data formats, create an MSX model from a file, and write 
the MSX model to a file.
"""
import logging
import json


logger = logging.getLogger(__name__)

def to_dict(msx) -> dict:
    """
    Convert a MsxModel into a dictionary
    
    Parameters
    ----------
    msx : MsxModel
        The MSX reaction model.

    Returns
    -------
    dict
        Dictionary representation of the MsxModel
    """
    return msx.to_dict()

def from_dict(d: dict):
    """
    Create or append a MsxModel from a dictionary

    Parameters
    ----------
    d : dict
        Dictionary representation of the water network model.

    Returns
    -------
    MsxModel
    
    """
    from wntr.msx.model import MsxModel
    return MsxModel.from_dict(d)

def write_json(msx, path_or_buf, as_library=False, indent=4, **kw_json):
    """
    Write the MSX model to a JSON file

    Parameters
    ----------
    msx : MsxModel
        The model to output.
    path_or_buf : str or IO stream
        Name of the file or file pointer.
    as_library : bool, optional
        Strip out network-specific elements if True, by default False.
    kw_json : keyword arguments
        Arguments to pass directly to :meth:`json.dump`.
    """
    d = to_dict(msx)
    if as_library:
        d.get('network_data', {}).get('initial_quality',{}).clear()
        d.get('network_data', {}).get('parameter_values',{}).clear()
        d.get('network_data', {}).get('sources',{}).clear()
        d.get('network_data', {}).get('patterns',{}).clear()
        d.get('options', {}).get('report',{}).setdefault('nodes', None)
        d.get('options', {}).get('report',{}).setdefault('links', None)
    if isinstance(path_or_buf, str):
        with open(path_or_buf, "w") as fout:
            json.dump(d, fout, indent=indent, **kw_json)
    else:
        json.dump(d, path_or_buf, indent=indent, **kw_json)

def read_json(path_or_buf, **kw_json):
    """
    Create or append a WaterNetworkModel from a JSON file

    Parameters
    ----------
    f : str
        Name of the file or file pointer.
    kw_json : keyword arguments
        Keyword arguments to pass to `json.load`.

    Returns
    -------
    MsxModel
    
    """
    if isinstance(path_or_buf, str):
        with open(path_or_buf, "r") as fin:
            d = json.load(fin, **kw_json)
    else:
        d = json.load(path_or_buf, **kw_json)
    return from_dict(d)

def write_msxfile(msx, filename):
    """
    Write an EPANET-MSX input file (.msx)

    Parameters
    ----------
    msx : MsxModel
        The model to write
    filename : str
        The filename to use for output
    """
    from wntr.epanet.msx.io import MsxFile
    MsxFile.write(filename, msx)

def read_msxfile(filename, append=None):
    """
    Read in an EPANET-MSX input file (.msx)
    
    Parameters
    ----------
    filename : str
        The filename to read in.
    append : MsxModel
        An existing model to add data into, by default None.
    """
    from wntr.epanet.msx.io import MsxFile
    return MsxFile.read(filename, append)

# coding: utf-8
"""Mulispecies reaction model I/O functions.

"""

import wntr.epanet.msx
import json

from wntr.utils.citations import Citation, to_jsontypes


def to_dict(msx):
    """Convert a multispecies reaction model to a dictionary representation"""
    from wntr import __version__
    rep = dict(
        version="wntr-{}".format(__version__),
        name=msx.name if msx.name else msx._msxfile,
        comment=msx.title if msx.title else "WaterQualityModel - units assumed to be internally consistent",
        citations=to_jsontypes(msx._citations),
        options=msx._options.to_dict(),
        variables=dict(
            species=[v.to_dict() for v in msx._species.values()],
            coefficients=[v.to_dict() for v in msx._coeffs.values()],
            other_terms=[v.to_dict() for v in msx._terms.values()],
        ),
        reactions=dict(
            pipes=[v.to_dict() for v in msx._pipe_dynamics.values()],
            tanks=[v.to_dict() for v in msx._tank_dynamics.values()],
        ),
        patterns=msx._patterns.copy(),
        initial_quality=msx._initial_quality.copy(),
    )
    # rep["sources"] = dict()
    # for sp, v in msx._sources:
    #     if v is not None and len(v) > 0:
    #         rep["sources"][sp] = dict()
    #         for node, source in v.items():
    #             rep["sources"][sp][node] = source.to_dict()
    return rep

def from_dict(d):
    raise NotImplementedError
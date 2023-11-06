# -*- coding: utf-8 -*-

r"""A library of common MSX reactions.


.. rubric:: Environment Variable

.. envvar:: WNTR_RXN_LIBRARY_PATH

    This environment variable, if set, will add additional folder(s) to the
    path to search for quality model files, (files with an ".msx", ".yaml", 
    or ".json" file extension).
    Multiple folders should be separated using the "``;``" character.
    See :class:`~wntr.msx.library.ReactionLibrary` for more details.    
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, ItemsView, Iterator, KeysView, List, Tuple, Union, ValuesView

from pkg_resources import resource_filename

from .base import ExpressionType, ReactionType, SpeciesType
from .model import MsxModel

try:
    import yaml

    yaml_err = None
except ImportError as e:
    yaml = None
    yaml_err = e

PIPE = ReactionType.PIPE
TANK = ReactionType.TANK
BULK = SpeciesType.BULK
WALL = SpeciesType.WALL
RATE = ExpressionType.RATE
EQUIL = ExpressionType.EQUIL
FORMULA = ExpressionType.FORMULA

logger = logging.getLogger(__name__)


def cite_msx() -> dict:
    """A citation generator for the EPANET-MSX user guide.

    Returns
    -------
    str
        Shang, F. and Rossman, L.A. and Uber, J.G. (2023) "EPANET-MSX 2.0 User Manual". (Cincinnati, OH: Water Infrastructure Division (CESER), U.S. Environmental Protection Agency). EPA/600/R-22/199.
    """
    return 'Shang, F. and Rossman, L.A. and Uber, J.G. (2023) "EPANET-MSX 2.0 User Manual". (Cincinnati, OH: Water Infrastructure Division (CESER), U.S. Environmental Protection Agency). EPA/600/R-22/199.'
    # return dict(
    #     entry_type="report",
    #     key="SRU23",
    #     fields=dict(
    #         title="EPANET-MSX 2.0 User Manual",
    #         year=2023,
    #         author="Shang, F. and Rossman, L.A. and Uber, J.G.",
    #         institution="Water Infrastructure Division (CESER), U.S. Environmental Protection Agency",
    #         location="Cincinnati, OH",
    #         number="EPA/600/R-22/199",
    #     ),
    # )


class ReactionLibrary:
    """A library of multispecies reaction definitions.

    This object can be accessed and treated like a dictionary, where keys are the model
    names and the values are the model objects.

    Paths are added/processed in the following order:

    1. the builtin directory of reactions,
    2. any paths specified in the environment variable described below, with directories listed
       first having the highest priority,
    3. any extra paths specified in the constructor, searched in the order provided.

    Once created, the library paths cannot be modified. However, a model can be added
    to the library using :meth:`add_model_from_file` or :meth:`add_models_from_dir`.
    """

    def __init__(self, extra_paths: List[str] = None, include_builtins=True, include_envvar_paths=True, load=True) -> None:
        """A library of multispecies reaction definitions.

        Parameters
        ----------
        extra_paths : list of str, optional
            user-specified list of reaction library directories, by default None
        include_builtins : bool, optional
            load files built-in with wntr, by default True
        include_envvar_paths : bool, optional
            load files from the paths specified in :envvar:`WNTR_RXN_LIBRARY_PATH`, by default True
        load : bool or str, optional
            load the files immediately on creation, by default True.

            If a string, then it will be passed as the `duplicates` argument
            to the load function. See :meth:`reset_and_reload` for details.

        Raises
        ------
        TypeError
            if `extra_paths` is not a list
        """
        if extra_paths is None:
            extra_paths = list()
        elif not isinstance(extra_paths, (list, tuple)):
            raise TypeError("Expected a list or tuple, got {}".format(type(extra_paths)))

        self.__library_paths = list()

        self.__data = dict()

        if include_builtins:
            default_path = os.path.abspath(resource_filename(__name__, "_library_data"))
            if default_path not in self.__library_paths:
                self.__library_paths.append(default_path)

        if include_envvar_paths:
            environ_path = os.environ.get("WNTR_RXN_LIBRARY_PATH", None)
            if environ_path:
                lib_folders = environ_path.split(";")
                for folder in lib_folders:
                    if folder not in self.__library_paths:
                        self.__library_paths.append(os.path.abspath(folder))

        for folder in extra_paths:
            self.__library_paths.append(os.path.abspath(folder))
        if load:
            if isinstance(load, str):
                self.reset_and_reload(duplicates=load)
            else:
                self.reset_and_reload()

    def __repr__(self) -> str:
        if len(self.__library_paths) > 3:
            return "{}(initial_paths=[{}, ..., {}])".format(self.__class__.__name__, repr(self.__library_paths[0]), repr(self.__library_paths[-1]))
        return "{}({})".format(self.__class__.__name__, repr(self.__library_paths))

    def path_list(self) -> List[str]:
        """Get the original list of paths used for this library.

        Returns
        -------
        list of str
            a copy of the paths used to **initially** populate this library
        """
        return self.__library_paths.copy()

    def reset_and_reload(self, duplicates: str = "error") -> List[Tuple[str, str, Any]]:
        """Load data from the configured directories into a library of models.

        Note, this function is not recursive and does not 'walk' any of the library's
        directories to look for subfolders.

        The ``duplicates`` argument specifies how models that have the same name,
        or that have the same filename if a name isn't specified in the file,
        are handled. **Warning**, if two files in the same directory have models
        with the same name, there is no guarantee which will be read in first.

        The first directory processed is the builtin library data. Next, any
        paths specified in the environment variable are searched in the order listed
        in the variable. Finally, any directories specified by the user in the 
        constructor are processed in the order listed.

        Parameters
        ----------
        duplicates : {"error" | "skip" | "replace"}, optional
            by default ``"error"``

            - A value of of ``"error"`` raises an exception and stops execution. 
            - A value of ``"skip"`` will skip models with the same `name` as a model that already
              exists in the library.
            - A value of ``"replace"`` will replace any existing model with a model that is read 
              in that has the same `name`.

        Returns
        -------
        (filename, reason, obj) : (str, str, Any)
            the file not read in, the cause of the problem, and the object that was skipped/overwritten
            or the exception raised

        Raises
        ------
        TypeError
            if `duplicates` is not a string
        ValueError
            if `duplicates` is not a valid value
        IOError
            if `path_to_folder` is not a directory
        KeyError
            if `duplicates` is ``"error"`` and two models have the same name
        """
        if duplicates and not isinstance(duplicates, str):
            raise TypeError("The `duplicates` argument must be None or a string")
        elif duplicates.lower() not in ["error", "skip", "replace"]:
            raise ValueError('The `duplicates` argument must be None, "error", "skip", or "replace"')

        load_errors = list()
        for folder in self.__library_paths:
            errs = self.add_models_from_dir(folder, duplicates=duplicates)
            load_errors.extend(errs)
        return load_errors

    def add_models_from_dir(self, path_to_dir: str, duplicates: str = "error") -> List[Tuple[str, str, Union[MsxModel, Exception]]]:
        """Load all valid model files in a folder.

        Note, this function is not recursive and does not 'walk' a directory tree.

        The ``duplicates`` argument specifies how models that have the same name,
        or that have the same filename if a name isn't specified in the file,
        are handled. **Warning**, if two files in the same directory have models
        with the same name, there is no guarantee which will be read in first.

        Parameters
        ----------
        path_to_dir : str
            the path to the folder to search
        duplicates : {"error", "skip", "replace"}, optional
            by default ``"error"``

            - A value of of ``"error"`` raises an exception and stops execution. 
            - A value of ``"skip"`` will skip models with the same `name` as a model that already
              exists in the library. 
            - A value of ``"replace"`` will replace any existing model with a model that is read 
              in that has the same `name`.

        Returns
        -------
        (filename, reason, obj) : tuple[str, str, Any]
            the file not read in, the cause of the problem, and the object that was skipped/overwritten
            or the exception raised

        Raises
        ------
        TypeError
            if `duplicates` is not a string
        ValueError
            if `duplicates` is not a valid value
        IOError
            if `path_to_folder` is not a directory
        KeyError
            if `duplicates` is ``"error"`` and two models have the same name
        """
        if duplicates and not isinstance(duplicates, str):
            raise TypeError("The `duplicates` argument must be None or a string")
        elif duplicates.lower() not in ["error", "skip", "replace"]:
            raise ValueError('The `duplicates` argument must be None, "error", "skip", or "replace"')
        if not os.path.isdir(path_to_dir):
            raise IOError("The following path is not valid/not a folder, {}".format(path_to_dir))
        load_errors = list()
        folder = path_to_dir
        files = os.listdir(folder)
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext is None or ext.lower() not in [".msx", ".json", ".yaml"]:
                continue
            if ext.lower() == ".msx":
                try:
                    new = MsxModel(file)
                except Exception as e:
                    logger.exception("Error reading file {}".format(os.path.join(folder, file)))
                    load_errors.append((os.path.join(folder, file), "load-failed", e))
                    continue
            elif ext.lower() == ".json":
                with open(os.path.join(folder, file), "r") as fin:
                    try:
                        new = MsxModel.from_dict(json.load(fin))
                    except Exception as e:
                        logger.exception("Error reading file {}".format(os.path.join(folder, file)))
                        load_errors.append((os.path.join(folder, file), "load-failed", e))
                        continue
            elif ext.lower() == ".yaml":
                if yaml is None:
                    logger.exception("Error reading file {}".format(os.path.join(folder, file)), exc_info=yaml_err)
                    load_errors.append((os.path.join(folder, file), "load-failed", yaml_err))
                    continue
                with open(os.path.join(folder, file), "r") as fin:
                    try:
                        new = MsxModel.from_dict(yaml.safe_load(fin))
                    except Exception as e:
                        logger.exception("Error reading file {}".format(os.path.join(folder, file)))
                        load_errors.append((os.path.join(folder, file), "load-failed", e))
                        continue
            else:  # pragma: no cover
                raise RuntimeError("This should be impossible to reach, since `ext` is checked above")
            new._orig_file = os.path.join(folder, file)
            if not new.name:
                new.name = os.path.splitext(os.path.split(file)[1])[0]
            if new.name not in self.__data:
                self.__data[new.name] = new
            else:  # this name exists in the library
                name = new.name
                if not duplicates or duplicates.lower() == "error":
                    raise KeyError('A model named "{}" already exists in the model; failed processing "{}"'.format(new.name, os.path.join(folder, file)))
                elif duplicates.lower() == "skip":
                    load_errors.append((new._orig_file, "skipped", new))
                    continue
                elif duplicates.lower() == "replace":
                    old = self.__data[name]
                    load_errors.append((old._orig_file, "replaced", old))
                    self.__data[name] = new
                else:  # pragma: no cover
                    raise RuntimeError("This should be impossible to get to, since `duplicates` is checked above")
        return load_errors

    def add_model_from_file(self, path_and_filename: str, name: str = None):
        """Load a reaction model from a file and add it to the model.

        Note, this **does not check** to see if a model exists with the same
        name, and it will automatically overwrite the existing model if one
        does exist.

        Parameters
        ----------
        path_to_file : str
            The full path and filename where the model is described.
        name : str, optional
            The name to use for the model instead of the name provided in the
            file or the filename, by default None
        """
        if not os.path.isfile(path_and_filename):
            raise IOError("The following path does not identify a file, {}".format(path_and_filename))

        ext = os.path.splitext(path_and_filename)[1]
        if ext is None or ext.lower() not in [".msx", ".json", ".yaml"]:
            raise IOError("The file is in an unknown format, {}".format(ext))
        if ext.lower() == ".msx":
            new = MsxModel(path_and_filename)
        elif ext.lower() == ".json":
            with open(path_and_filename, "r") as fin:
                new = MsxModel.from_dict(json.load(fin))
        elif ext.lower() == ".yaml":
            if yaml is None:
                raise RuntimeError("Unable to import yaml") from yaml_err
            with open(path_and_filename, "r") as fin:
                new = MsxModel.from_dict(yaml.safe_load(fin))
        else:  # pragma: no cover
            raise RuntimeError("This should be impossible to reach, since ext is checked above")
        new._orig_file = path_and_filename
        if not new.name:
            new.name = os.path.splitext(os.path.split(path_and_filename)[1])[0]
        if name is not None:
            new.name = name
        self.__data[new.name] = new

    def get_model(self, name: str) -> MsxModel:
        """Get a reaction model from the library by model name.

        Parameters
        ----------
        name : str
            the name of the model

        Returns
        -------
        MsxModel
            the model object
        """
        return self.__data[name]

    def model_name_list(self) -> List[str]:
        """Get the names of all models in the library.
        
        Returns
        -------
        list of str
            list of model names
        """
        return list(self.keys())

    def __getitem__(self, __key: Any) -> Any:
        return self.__data.__getitem__(__key)

    def __setitem__(self, __key: Any, __value: Any) -> None:
        return self.__data.__setitem__(__key, __value)

    def __delitem__(self, __key: Any) -> None:
        return self.__data.__delitem__(__key)

    def __contains__(self, __key: object) -> bool:
        return self.__data.__contains__(__key)

    def __iter__(self) -> Iterator:
        return self.__data.__iter__()

    def __len__(self) -> int:
        return self.__data.__len__()

    def keys(self) -> KeysView:
        return self.__data.keys()

    def items(self) -> ItemsView:
        return self.__data.items()

    def values(self) -> ValuesView:
        return self.__data.values()

    def clear(self) -> None:
        return self.__data.clear()

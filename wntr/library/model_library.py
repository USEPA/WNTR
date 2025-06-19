from os.path import abspath, dirname, basename, join, isdir
import glob
from wntr.network import WaterNetworkModel

libdir = dirname(abspath(str(__file__)))

class ModelLibrary:
    """
    Model library class to manage water network models.
    Parameters
    ----------
    directories : list of str
        Directories containing INP files.
    """

    def __init__(self, directories=None):
        if directories is None:
            directories = [join(libdir, "networks")]
        self._directories = []
        for directory in directories:
            self.add_directory(directory)

    def _build_model_library(self):
        """
        Scan directories for INP files.  Files with the same name
        will override previous files (based on the order of directories)
        """
        self._model_library = {}
        for directory in self._directories:
            for file in glob.glob(join(directory, '*.inp')):
                model_name = basename(file).split('.')[0]
                self._model_library[model_name] = join(directory, file)
    
    @property
    def model_name_list(self):
        """
        Return a list of model names in the library.
        Returns
        -------
        list of str
        """
        return list(self._model_library.keys())
    
    @property
    def directories(self):
        return self._directories

    def add_directory(self, directory):
        assert isinstance(directory, str)
        
        if not isdir(directory):
            raise ValueError(f"Provided path '{directory}' is not a valid directory.")
        self._directories.append(abspath(directory))
        self._build_model_library()
        
    def get_filepath(self, name):
        """
        Get the file path of a model by its name.
        Parameters
        ----------
        name : str
            Name of the model.
        Returns
        -------
        str
            File path of the model's INP file.
        """
        if name not in self._model_library:
            raise KeyError(f"Model '{name}' not found in the library.")
        return self._model_library[name]

    def get_model(self, name):
        """
        Get a WaterNetworkModel by its name.
        Parameters
        ----------
        name : str
            Name of the model.
        Returns
        -------
        WaterNetworkModel
        """
        if name not in self._model_library:
            raise KeyError(f"Model '{name}' not found in the library.")
        return WaterNetworkModel(self._model_library[name])

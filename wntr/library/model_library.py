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
        self.directories = directories

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
    @directories.setter
    def directories(self, directories):
        assert isinstance(directories, list)
        
        for directory in directories:
            if not isdir(directory):
                raise ValueError(f"Provided path '{directory}' is not a valid directory.")
        self._directories = directories
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


    # def add_model(self, name, wn_model):
    #     """
    #     Add a new WaterNetworkModel to the library.
    #     Parameters
    #     ----------
    #     name : str
    #         Name of the model.
    #     wn_model : WaterNetworkModel
    #         WaterNetworkModel object to add to the library.
    #     """
    #     if name in self._model_paths:
    #         raise KeyError(f"Model '{name}' already exists in the library.")
    #     if not isinstance(wn_model, WaterNetworkModel):
    #         raise TypeError("The provided model must be a WaterNetworkModel object.")

    #     # Save the model to the directory
    #     file_path = os.path.join(self.directory_path, f"{name}.inp")
    #     wntr.network.io.write_inpfile(wn_model, file_path)
    #     self._model_paths[name] = file_path
    #     self._build_model_paths()

    # def remove_model(self, name):
    #     """
    #     Remove a model from the library.
    #     Parameters
    #     ----------
    #     name : str
    #         Name of the model to remove.
    #     """
    #     if name not in self._model_paths:
    #         raise KeyError(f"Model '{name}' not found in the library.")
    #     os.remove(self._model_paths[name])
    #     del self._model_paths[name]

    # def copy_model(self, source_name, target_name):
    #     """
    #     Copy an existing model to create a new model entry.
    #     Parameters
    #     ----------
    #     source_name : str
    #         Name of the existing model to copy.
    #     target_name : str
    #         Name of the new model.
    #     """
    #     if source_name not in self._model_paths:
    #         raise KeyError(f"Source model '{source_name}' not found in the library.")
    #     if target_name in self._model_paths:
    #         raise KeyError(f"Target model '{target_name}' already exists in the library.")

    #     # Load the source model
    #     source_model = self.get_model(source_name)

    #     # Add the copied model with the new name
    #     self.add_model(target_name, source_model)
    #     self._build_model_paths()
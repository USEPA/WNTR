import os
import wntr
from wntr.network import WaterNetworkModel

class ModelLibrary:
    """
    Model library class to manage water network models.

    Parameters
    ----------
    directory_path : str
        Path to a directory containing INP files.
    """

    def __init__(self, directory_path=None):
        if directory_path is None:
            this_file_path = os.path.dirname(os.path.abspath(__file__))
            directory_path = os.path.join(this_file_path, "networks")
        if not os.path.isdir(directory_path):
            raise ValueError(f"Provided path '{directory_path}' is not a valid directory.")
        self.directory_path = directory_path
        self._model_paths = {}

        # Scan directory recursively for INP files
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if file.endswith('.inp'):
                    model_name = os.path.splitext(file)[0]
                    self._model_paths[model_name] = os.path.join(root, file)

    @property
    def model_name_list(self):
        """
        Return a list of model names in the library.

        Returns
        -------
        list of str
        """
        return list(self._model_paths.keys())

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
        if name not in self._model_paths:
            raise KeyError(f"Model '{name}' not found in the library.")
        return self._model_paths[name]

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
        if name not in self._model_paths:
            raise KeyError(f"Model '{name}' not found in the library.")
        return WaterNetworkModel(self._model_paths[name])

    def add_model(self, name, wn_model):
        """
        Add a new WaterNetworkModel to the library.

        Parameters
        ----------
        name : str
            Name of the model.
        wn_model : WaterNetworkModel
            WaterNetworkModel object to add to the library.
        """
        if name in self._model_paths:
            raise KeyError(f"Model '{name}' already exists in the library.")
        if not isinstance(wn_model, WaterNetworkModel):
            raise TypeError("The provided model must be a WaterNetworkModel object.")

        # Save the model to the directory
        file_path = os.path.join(self.directory_path, f"{name}.inp")
        wntr.network.io.write_inpfile(wn_model, file_path)
        self._model_paths[name] = file_path

    def remove_model(self, name):
        """
        Remove a model from the library.

        Parameters
        ----------
        name : str
            Name of the model to remove.
        """
        if name not in self._model_paths:
            raise KeyError(f"Model '{name}' not found in the library.")
        os.remove(self._model_paths[name])
        del self._model_paths[name]

    def copy_model(self, source_name, target_name):
        """
        Copy an existing model to create a new model entry.

        Parameters
        ----------
        source_name : str
            Name of the existing model to copy.
        target_name : str
            Name of the new model.
        """
        if source_name not in self._model_paths:
            raise KeyError(f"Source model '{source_name}' not found in the library.")
        if target_name in self._model_paths:
            raise KeyError(f"Target model '{target_name}' already exists in the library.")

        # Load the source model
        source_model = self.get_model(source_name)

        # Add the copied model with the new name
        self.add_model(target_name, source_model)
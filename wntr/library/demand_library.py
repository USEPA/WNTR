import matplotlib.pylab as plt
import pandas as pd
import numpy as np
import scipy.stats
import json
from os.path import abspath, dirname, join

from wntr.network.elements import Pattern
from wntr.network.options import TimeOptions

libdir = dirname(abspath(str(__file__)))
NoneType = type(None)

class DemandPatternLibrary(object):
    """
    Demand pattern library class.
    
    Parameters
    -------------------
    filename_or_data: str (optional)
        Filename or JSON data containing a demand pattern library.
        If None, the default DemandPatternLibrary.json file is loaded.
    """
    
    def __init__(self, filename_or_data=None):
        
        self.library = {}
        if isinstance(filename_or_data, NoneType):
            filename = join(libdir, 'DemandPatternLibrary.json')
            with open(filename, "r") as fin:
                data = json.load(fin)
        elif isinstance(filename_or_data, str):
            filename = filename_or_data
            with open(filename, "r") as fin:
                data = json.load(fin)
        elif isinstance(filename_or_data, list):
            data = filename_or_data
        
        for entry in data:
            name = entry['name']
            self.add_pattern(name, entry)
    
    @property
    def pattern_name_list(self):
        """
        Return a list of demand pattern entry names
        
        Returns
        -------
        list of strings
        """
        
        return list(self.library.keys())
    
    def get_pattern(self, name):
        """
        Return a pattern entry from the demand pattern library
        
        Parameters
        ----------
        name : str
            Pattern name
            
        Returns
        -------
        dictionary
        """
        
        assert isinstance(name, str)
        
        return self.library[name]
    
    def remove_pattern(self, name):
        """
        Remove a pattern from the demand pattern library
        
        Parameters
        ----------
        name : str
            Pattern name
        """
        
        assert isinstance(name, str)
        assert name in set(self.pattern_name_list)
        
        del self.library[name]
    
    def copy_pattern(self, name, new_name):
        """
        Add a copy of an existing pattern to the library
        
        Parameters
        ----------
        name : str
            Existing pattern name
        new_name : str
            New pattern name
        """
        
        assert isinstance(name, str)
        assert isinstance(new_name, str)
        assert name != new_name

        entry = self.get_pattern(name).copy()
        entry['name'] = new_name
        self.add_pattern(new_name, entry)

    def filter_by_category(self, category):
        """
        Return a subset of the library, filtered by category
        
        Parameters
        ----------
        category : str
            Category name
            
        Returns
        -------
        list of dictionaries
        """
        
        assert isinstance(category, (str, NoneType))

        subset = []
        for name in self.pattern_name_list:
            entry = self.get_pattern(name)
            if entry['category'] == category:
                subset.append(entry)

        return subset

    def normalize_pattern(self, name, inplace=True):
        """
        Normalize values in a pattern so the mean equals 1
        
        Parameters
        ----------
        name : str
            Pattern name
        inplace : bool
            Indicates if the pattern should be modified in place
        
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(inplace, bool)
        
        series = self.to_Series(name, duration=None)
        if series.min() < 0:
            series = series - series.min()
        series = series/series.mean()
        
        if inplace:
            self.library[name]['multipliers'] = list(series)
        
        return series
    
    def apply_noise(self, name, std, normalize=False, seed=None, inplace=True):
        """
        Apply gaussian random noise to a pattern
        
        Parameters
        ----------
        name : str
            Pattern name
        std : int or float
            Standard deviation
        normalize : bool
            Indicates if the pattern should be normalized
        seed : int
            Seed for the gaussian distribution
        inplace : bool
            Indicates if the pattern should be modified in place
        
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(std, (int, float))
        assert isinstance(normalize, bool)
        assert isinstance(seed, (int, NoneType))
        assert isinstance(inplace, bool)
        
        np.random.seed(seed)
        
        series = self.to_Series(name, duration=None)
        
        noise = np.random.normal(0, std, len(series))
        series = series + noise

        if normalize:
            series = series/series.mean()

        if inplace:
            self.library[name]['multipliers'] = list(series)
        
        return series
        
    def resample_multipliers(self, name, duration=86400, 
                             pattern_timestep=3600, start_clocktime=0,
                             wrap=True, inplace=True):
        """
        Resample multipliers, which can change if the start_clocktime, 
        pattern_timestep, or wrap status changes
        
        Parameters
        ----------
        name : str
            Pattern name
        duration : int or float
            Duration (in seconds) of the resampled pattern
        pattern_timestep : int
            Timestep (in seconds) of the resampled pattern
        start_clocktime : int
            Time of day (in seconds from midnight) at which pattern begins
        wrap : bool
            Indicates if the sequence of pattern values repeats
        inplace : bool
            Indicates if the pattern should be modified in place
        
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(duration, (int, float))
        assert isinstance(pattern_timestep, int)
        assert isinstance(start_clocktime, int)
        assert isinstance(wrap, bool)
        assert isinstance(inplace, bool)
        
        # Pattern defined using the current time parameters
        entry = self.get_pattern(name)
        entry_start_clocktime = entry['start_clocktime']

        pattern = self.to_Pattern(name)
        
        # index uses new time parameters
        index = np.arange(start_clocktime, duration, pattern_timestep)
        multipliers = []
        for i in index:
            multipliers.append(pattern.at(i-entry_start_clocktime))
        
        if inplace:
            self.library[name]['start_clocktime'] = start_clocktime
            self.library[name]['pattern_timestep'] = pattern_timestep
            self.library[name]['wrap'] = wrap
            self.library[name]['multipliers'] = list(multipliers)
        
        series = pd.Series(index=index, data=multipliers)
        
        return series
    
    def add_pattern(self, name, entry):
        """
        Add a pattern to the library
        
        Parameters
        ----------
        name : str
            Pattern name
        entry : dict
            Pattern entry which contains the following dictionary keys
            
            * name: Pattern name (string)
            * category: Pattern category (string, optional)
            * description: Pattern description (string, optional)
            * citation: Pattern citation (string, optional)
            * start_clocktime: Time of day (in seconds from midnight) at which pattern begins (integer)
            * pattern_timestep: Pattern timestep in seconds (integer)
            * wrap: Indicates if the sequence of pattern values repeats (True or False)
            * multipliers: Pattern values (list of floats)
        
        Returns
        -------
        pandas Series
        """

        assert isinstance(name, str)
        assert isinstance(entry, dict)
        assert name not in set(self.pattern_name_list)
        
        required_keys = ['name', 
                         'start_clocktime', 
                         'pattern_timestep', 
                         'wrap', 
                         'multipliers']
        assert set(required_keys) <= set(entry.keys())

        self.library[name] = entry
        series = self.to_Series(name)
        
        return series
        
    def add_pulse_pattern(self, name, on_off_sequence, duration=86400, 
                          pattern_timestep=3600, start_clocktime=0, 
                          wrap=True, invert=False, normalize=False):
        """
        Add a pulse pattern to the library using a sequence of on/off times
        
        Pulse patterns can be used to model sudden changes in water demand, 
        for example, from a fire hydrant.
        
        This pattern replicates functionality in Pattern.binary_pattern
        
        Parameters
        ----------
        name : str
            Pattern name
        on_off_sequence : list
            A list of times to turn the pattern on/off (starting with on)
        duration : int or float
            Duration (in seconds) of the resampled pattern
        pattern_timestep : int
            Timestep (in seconds) of the resampled pattern
        start_clocktime : int
            Time of day (in seconds from midnight) at which pattern begins
        wrap : bool
            Indicates if the sequence of pattern values repeats
        invert : bool
            Indicates if the on/off values should be switched
        normalize : bool
            Indicates if the pattern should be normalized
        
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(on_off_sequence, list)
        assert np.all(np.diff(on_off_sequence) > 0) # is monotonically increasing
        assert isinstance(duration, (int, float))
        assert isinstance(pattern_timestep, int)
        assert isinstance(start_clocktime, int)
        assert isinstance(wrap, bool)
        assert isinstance(invert, bool)
        assert isinstance(normalize, bool)

        index = np.arange(start_clocktime, duration, pattern_timestep)
        multipliers = pd.Series(index=index, data=0) # starts off
        switches = 0
        for time in on_off_sequence:
            switches = switches + 1
            position = np.mod(switches,2) # returns 0 or 1
            multipliers.loc[time::] = position

        if invert:
            multipliers = multipliers.max() - multipliers

        if normalize:
            multipliers = multipliers/multipliers.mean()

        entry = {'name': name,
                 'category': None,
                 'description': None,
                 'citation': None,
                 'start_clocktime': start_clocktime,
                 'pattern_timestep': pattern_timestep,
                 'wrap': wrap,
                 'multipliers': list(multipliers)}

        self.add_pattern(name, entry)
        series = self.to_Series(name)
        
        return series

    def add_gaussian_pattern(self, name, mean, std, duration=86400, 
                             pattern_timestep=3600, start_clocktime=0, 
                             wrap=True, invert=False, normalize=False):
        """
        Add a Guassian pattern to the library defined by a mean and standard
        deviation
        
        Gaussian patterns can be used to model water demand that gradually 
        increases to a max water use, followed by gradual decline.
        
        Parameters
        ----------
        name : str
            Pattern name
        mean : int or float
            Mean of the Guassian distribution
        std : int or float
            Standard deviation of the Guassian distribution
        duration : int or float
            Duration (in seconds) of the pattern
        pattern_timestep : int
            Timestep (in seconds) of the pattern
        start_clocktime : int
            Time of day (in seconds from midnight) at which pattern begins
        wrap : bool
            Indicates if the sequence of pattern values repeats
        invert : bool
            Indicates if the on/off values should be switched
        normalize : bool
            Indicates if the pattern should be normalized
            
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(mean, (int, float))
        assert isinstance(std, (int, float))
        assert isinstance(duration, (int, float))
        assert isinstance(pattern_timestep, int)
        assert isinstance(start_clocktime, int)
        assert isinstance(wrap, bool)
        assert isinstance(invert, bool)
        assert isinstance(normalize, bool)
        
        index = np.arange(start_clocktime, duration, pattern_timestep)
        multipliers = scipy.stats.norm.pdf(index, mean, std)

        if invert:
            multipliers = multipliers.max() - multipliers

        if normalize:
            multipliers = multipliers/multipliers.mean()

        entry = {'name': name,
                 'category': None,
                 'description': None,
                 'citation': None,
                 'start_clocktime': start_clocktime,
                 'pattern_timestep': pattern_timestep,
                 'wrap': wrap,
                 'multipliers': list(multipliers)}

        self.add_pattern(name, entry)
        series = self.to_Series(name)
        
        return series

    def add_triangular_pattern(self, name, start, peak, end, duration=86400, 
                               pattern_timestep=3600, start_clocktime=0,
                               wrap=True, invert=False, normalize=False):
        """
        Add a triangular pattern to the library defined by a start time,
        peak time, and end time
        
        Triangular patterns can be used to model water demand that uniformly 
        increases to a max water use, followed by uniform decline.
        
        Parameters
        ----------
        name : str
            Pattern name
        start : int or float
            Start time (in seconds) of the triangular distribution
        peak : int or float
            Peak time (in seconds) of the triangular distribution
        end : int or float
            End time (in seconds) of the triangular distribution
        duration : int or float
            Duration (in seconds) of the pattern
        pattern_timestep : int
            Timestep (in seconds) of the pattern
        start_clocktime : int
            Time of day (in seconds from midnight) at which pattern begins
        wrap : bool
            Indicates if the sequence of pattern values repeats
        invert : bool
            Indicates if the on/off values should be switched
        normalize : bool
            Indicates if the pattern should be normalized
            
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(start, (int, float))
        assert isinstance(peak, (int, float))
        assert isinstance(end, (int, float))
        assert isinstance(duration, (int, float))
        assert isinstance(pattern_timestep, int)
        assert isinstance(start_clocktime, int)
        assert isinstance(wrap, bool)
        assert isinstance(invert, bool)
        assert isinstance(normalize, bool)
        
        loc = start
        scale = end-start
        c = (peak-start)/(end-start)

        index = np.arange(start_clocktime, duration, pattern_timestep)
        multipliers = scipy.stats.triang.pdf(index, c, loc, scale)

        if invert:
            multipliers = multipliers.max() - multipliers

        if normalize:
            multipliers = multipliers/multipliers.mean()

        entry = {'name': name, 
                 'category': None,
                 'description': None,
                 'citation': None,
                 'start_clocktime': start_clocktime,
                 'pattern_timestep': pattern_timestep,
                 'wrap': wrap,
                 'multipliers': list(multipliers)}

        self.add_pattern(name, entry)
        series = self.to_Series(name)
        
        return series
    
    def add_combined_pattern(self, name, patterns_to_combine, combine='Overlap', weights=None, 
                             durations=[86400], pattern_timestep=3600, start_clocktime=0,
                             wrap=True, normalize=False):
        """
        Combine patterns (overlap or sequential) to create a new pattern
        
        Parameters
        ----------
        name : str
            Pattern name
        patterns_to_combine : list of str
            List of pattern names to combine
        combine : str
            Combine method, Overlap or Sequential
        weights: list
            List of weight applied to each pattern.  
            If no weights are provided (None), then the patterns are equally 
            weighted.
        durations : list of ints or floats
            If combine method is Overlap, the list contains only one entry 
            which is the total duration of the pattern (in seconds).
            If combine method is Sequential, the list contains one duration 
            for each pattern to combine (in seconds).
        pattern_timestep : int
            Timestep (in seconds) of the pattern
        start_clocktime : int
            Time of day (in seconds from midnight) at which pattern begins
        wrap : bool
            Indicates if the sequence of pattern values repeats
        normalize : bool
            Indicates if the pattern should be normalized
            
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(patterns_to_combine, list)
        if weights is None:
            weights = [1]*len(patterns_to_combine)
        assert isinstance(weights, list)
        assert len(patterns_to_combine) == len(weights)
        assert isinstance(combine, str)
        assert combine in ['Overlap', 'Sequential']
        assert isinstance(durations, list)
        if combine == 'Overlap':
            assert len(durations) == 1
        else:
            assert len(durations) == len(patterns_to_combine)
        assert isinstance(pattern_timestep, int)
        assert isinstance(start_clocktime, int)
        assert isinstance(wrap, bool)
        assert isinstance(normalize, bool)
        
        t = start_clocktime
        series = {}
        for i, n in enumerate(patterns_to_combine):
            if combine == 'Sequential':
                duration = durations[i]   
            else:
                duration = durations[0]
            weight = weights[i]
            
            entry = self.get_pattern(n)
            #entry_start_clocktime = entry['start_clocktime']
            
            pattern = self.to_Pattern(n)
    
            index = np.arange(t, t+duration, pattern_timestep)
            values = []
            for i in index:
                values.append(pattern.at(i-start_clocktime))
    
            series[n+str(i)] = pd.Series(index=index, data=values*weight)
            
            if combine == 'Sequential':
                t = t + duration
        
        df = pd.DataFrame(index=index, data=series)
        
        if combine == 'Sequential':
            series = pd.concat(series)
            series.droplevel(0)
        else:
            series = df.sum(axis=1)
    
        if normalize:
            series = series/series.mean()
    
        entry = {'name': name, 
                 'category': None,
                 'description': None,
                 'citation': None,
                 'start_clocktime': start_clocktime,
                 'pattern_timestep': pattern_timestep,
                 'wrap': wrap,
                 'multipliers': list(series)}
    
        self.add_pattern(name, entry)
        
        return series

    def to_Pattern(self, name, time_options=None):
        """
        Convert the pattern library entry to a WNTR Pattern
        
        Parameters
        ----------
        name : str
            Pattern name
        time_options : None or tuple 
            Time options (pattern_start, pattern_timestep, pattern_interpolation)
            If None, then time options from the pattern are used (in seconds).
    
        Returns
        -------
        WNTR Pattern object
        """
        
        assert isinstance(name, str)
        assert isinstance(time_options, (TimeOptions, tuple, NoneType))
    
        entry = self.get_pattern(name)
        pattern_timestep = entry['pattern_timestep']
        start_clocktime = entry['start_clocktime']
        
        if time_options is None:
            pattern_start = 0
            pattern_interpolation=True
            time_options = (pattern_start, 
                            pattern_timestep, 
                            pattern_interpolation)
        elif isinstance(time_options, TimeOptions):
            assert time_options.pattern_timestep == pattern_timestep
            assert time_options.start_clocktime == start_clocktime
        elif isinstance(time_options, tuple):
            assert time_options[1] == pattern_timestep
            
        # Note pattern_start is only used by the EpanetSimulator or WNTRSimulator
        multipliers = entry['multipliers']
        wrap = entry['wrap']
        pattern = Pattern(name=name,
                          multipliers=multipliers,
                          time_options=time_options,
                          wrap=wrap)

        return pattern

    def to_Series(self, name, duration=None):
        """
        Convert the pattern library entry to a Pandas Series
        
        Parameters
        ----------
        name : str
            Pattern name
        duration : int, float, or None
            Pattern duration (in seconds).  If None, then the duration from 
            the pattern entry is used.
        
        Returns
        -------
        pandas Series
        """
        
        assert isinstance(name, str)
        assert isinstance(duration, (int, float, NoneType))
        
        entry = self.get_pattern(name)

        start_clocktime = entry['start_clocktime']
        pattern_timestep = entry['pattern_timestep']
        if duration is None:
            multipliers = entry['multipliers']
            duration = start_clocktime + len(multipliers)*pattern_timestep

        pattern = self.to_Pattern(name)

        # Get values at a particular time, can be used to resample
        index = np.arange(start_clocktime, duration, pattern_timestep)
        data = []
        for i in index:
            data.append(pattern.at(i-start_clocktime))
        series = pd.Series(index=index, data=data)

        return series

    def write_json(self, filename):
        """
        Write the library to a JSON file
        
        Parameters
        ----------
        filename : str
            Filename for the library JSON file
        """
        
        assert isinstance(filename, str)
        
        data = []
        for name, entry in self.library.items():
            data.append(entry)
            
        if isinstance(filename, str):
            with open(filename, "w") as fout:
                json.dump(data, fout)

    def plot_patterns(self, names=None, duration=None, ax=None):
        """
        Plot patterns
        
        Parameters
        ----------
        names : list of str
            Pattern names, if None then all patterns are plotted
        duration : int or float
            Pattern duration (in seconds).  If None, then the duration from 
            the pattern entry is used.
        
        Returns
        -------
        matplotlib axes object  
        """
        
        assert isinstance(names, (list, NoneType))
        assert isinstance(duration, (int, float, NoneType))
        
        if names is None:
            names = self.pattern_name_list

        if ax is None:
            fig, ax = plt.subplots()

        for name in names:
            series = self.to_Series(name, duration=duration)
            series.index = series.index/3600
            series.plot(ax=ax, linewidth=1.5, label=name)
            
        ax.set_ylabel('Demand Multiplier')
        ax.set_xlabel('Time (hr)')
        ax.legend()

        return ax

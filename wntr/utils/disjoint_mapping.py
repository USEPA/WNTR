# coding: utf-8
"""
A set of utility classes that is similar to the 'registry' objects in the wntr.network
class, but more general, and therefore usable for other extensions, such as multi-species
water quality models.
"""

from collections.abc import MutableMapping
from typing import Any, Dict, Hashable, ItemsView, Iterator, KeysView, Set, ValuesView


class WrongGroupError(KeyError):
    """The key exists but is in a different disjoint group"""
    pass


class KeyExistsError(KeyError):
    """The name already exists in the model"""
    pass


class DisjointMapping(MutableMapping):
    """A mapping with keys that are also divided into disjoint groups of keys.

    The main purpose of this utility class is to perform implicit name collision checking
    while also allowing both the groups and the main dictionary to be used as dictionaries
    -- i.e., using `__*item__` methods and `mydict[key]` methods.
    """

    __data: Dict[Hashable, Hashable] = None
    __key_groupnames: Dict[Hashable, str] = None
    __groups: Dict[str, "DisjointMappingGroup"] = None
    __usage: Dict[Hashable, Set[Any]] = None

    def __init__(self, *args, **kwargs):
        self.__data: Dict[Hashable, Any] = dict(*args, **kwargs)
        self.__key_groupnames: Dict[Hashable, str] = dict()
        self.__groups: Dict[str, "DisjointMappingGroup"] = dict()
        self.__usage: Dict[Hashable, Set[Any]] = dict()
        for k, v in self.__data.items():
            self.__key_groupnames[k] = None
            self.__usage[k] = set()

    def add_disjoint_group(self, name, cls = None):
        if name in self.__groups.keys():
            raise KeyError("Disjoint group already exists within registry")
        if cls is None:
            new = DisjointMappingGroup(name, self)
        elif issubclass(cls, DisjointMappingGroup):
            new = cls(name, self)
        else:
            raise TypeError('cls must be a subclass of DisjointMappingGroup, got {}'.format(cls))
        self.__groups.__setitem__(name, new)
        return new

    def get_disjoint_group(self, name: str):
        return self.__groups[name]

    def get_groupname(self, _key: Hashable):
        return self.__key_groupnames[_key]

    def add_item_to_group(self, groupname, key, value):
        current = self.__key_groupnames.get(key, None)
        if current is not None and groupname != current:
            raise WrongGroupError("The key '{}' is already used in a different group '{}'".format(key, groupname))
        if groupname is not None:
            group = self.__groups[groupname]
            group._data.__setitem__(key, value)
        self.__key_groupnames[key] = groupname
        return self.__data.__setitem__(key, value)

    def move_item_to_group(self, new_group_name, key):
        value = self.__data[key]
        current = self.get_groupname(key)
        if new_group_name is not None:
            new_group = self.__groups[new_group_name]
            new_group._data[key] = value
        if current is not None:
            old_group = self.__groups[current]
            old_group._data.__delitem__(key)
        self.__key_groupnames[key] = new_group_name

    def remove_item_from_group(self, groupname, key):
        current = self.__key_groupnames.get(key, None)
        if groupname != current:
            raise WrongGroupError("The key '{}' is in a different group '{}'".format(key, groupname))
        if groupname is not None:
            self.__groups[groupname]._data.__delitem__(key)

    def __getitem__(self, __key: Any) -> Any:
        return self.__data.__getitem__(__key)

    def __setitem__(self, __key: Any, __value: Any) -> None:
        current = self.__key_groupnames.get(__key, None)
        if current is not None:
            self.__groups[current]._data[__key] = __value
        return self.__data.__setitem__(__key, __value)

    def __delitem__(self, __key: Any) -> None:
        current = self.__key_groupnames.get(__key, None)
        if current is not None:
            self.__groups[current]._data.__delitem__(__key)
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
        raise RuntimeError("You cannot clear this")

    def popitem(self) -> tuple:
        raise RuntimeError("You cannot pop this")


class DisjointMappingGroup(MutableMapping):
    """A dictionary that checks a namespace for existing entries.

    To create a new instance, pass a set to act as a namespace. If the namespace does not
    exist, a new namespace will be instantiated. If it does exist, then a new, disjoint
    dictionary will be created that checks the namespace keys before it will allow a new
    item to be added to the dictionary. An item can only belong to one of the disjoint dictionaries
    associated with the namespace.

    Examples
    --------
    Assume there is a namespace `nodes` that has two distinct subsets of objects, `tanks`
    and `reservoirs`. A name for a tank cannot also be used for a reservoir, and a node
    cannot be both a `tank` and a `reservoir`. A DisjointNamespaceDict allows two separate
    dictionaries to be kept, one for each subtype, but the keys within the two dictionaries
    will be ensured to not overlap.

    Parameters
    ----------
    __keyspace : set
        the name of the namespace for consistency checking
    args, kwargs : Any
        regular arguments and keyword arguments passed to the underlying dictionary

    """

    __name: str = None
    __keyspace: "DisjointMapping" = None
    _data: dict = None

    def __new__(cls, name: str, _keyspace: "DisjointMapping"):
        if name is None:
            raise TypeError("A name must be specified")
        if _keyspace is None:
            raise TypeError("A registry must be specified")
        newobj = super().__new__(cls)
        return newobj

    def __init__(self, name: str, _keyspace: "DisjointMapping"):
        if name is None:
            raise TypeError("A name must be specified")
        if _keyspace is None:
            raise TypeError("A registry must be specified")
        self.__name: str = name
        self.__keyspace: DisjointMapping = _keyspace
        self._data = dict()

    def __getitem__(self, __key: Any) -> Any:
        return self._data[__key]

    def __setitem__(self, __key: Any, __value: Any) -> None:
        return self.__keyspace.add_item_to_group(self.__name, __key, __value)

    def __delitem__(self, __key: Any) -> None:
        return self.__keyspace.remove_item_from_group(self.__name, __key)

    def __contains__(self, __key: object) -> bool:
        return self._data.__contains__(__key)

    def __iter__(self) -> Iterator:
        return self._data.__iter__()

    def __len__(self) -> int:
        return self._data.__len__()

    def keys(self) -> KeysView:
        return self._data.keys()

    def items(self) -> ItemsView:
        return self._data.items()

    def values(self) -> ValuesView:
        return self._data.values()

    def clear(self) -> None:
        raise RuntimeError("Cannot clear a group")

    def popitem(self) -> tuple:
        raise RuntimeError("Cannot pop from a group")

    def __repr__(self) -> str:
        return "{}(name={}, data={})".format(self.__class__.__name__, repr(self.__name), self._data)

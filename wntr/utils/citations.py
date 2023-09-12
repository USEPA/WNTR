# coding: utf-8
"""Contains a dataclass that can be used to store citations.
"""
from __future__ import annotations
import dataclasses

import datetime
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, Union, List, Tuple

Literal = str
"""A literal string"""
Name = str
"""A name string, preferrably in order without commas"""
NameList = Union[Name, List[Name]]
"""A list of names, or a string with "and" between names"""
LiteralList = Union[Literal, List[Literal]]
"""A list of literals, or a string with "and" between literals"""
Key = str
"""A string that comes from a limited set of values"""
KeyList = Union[Key, List[Key]]
"""A list of keys, or a string with "and" between keys"""
Verbatim = str
"""A string that should not be interpreted (ie raw)"""
Special = Any
"""Anything that isn't a string or list of strings"""
URI = str
"""A valid URI"""
Date = Union[str, datetime.date]
"""A date or string in yyyy-mm-dd format (must be 0-padded, eg 2021-02-02 for February 2, 2021"""
Range = Union[str, Tuple[Any, Any]]
"""A 2-tuple of (start,stop) or a string with two values separated by '--' """
SeparatedValues = Union[str, List[str]]
"""A list of strings, or a string that is delimited (the delimiter is not specified)"""


@dataclass(repr=False)
class Citation:
    """A class to hold a citation to document the source of a model.
    
    Parameters
    ----------
    entry_type : str
        Describe the type of citation, for example, 'journal' or 'book'.
    key : str
        A key to use to identify this citation. Usually a BibTeX key or an
        alphanumeric key per citation standards.
    fields : CitationFields
        An object that has attributes that align with different citation
        fields, such as 'title' or 'author'.
    """

    entry_type: str
    key: str
    fields: "CitationFields" = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = CitationFields(None)
        elif isinstance(self.fields, dict):
            self.fields = CitationFields(**self.fields)
        elif isinstance(self.fields, list):
            self.fields = CitationFields(*self.fields)

    def to_dict(self):
        """Convert to a dictionary.

        Returns
        -------
        dict
            the citation dictionary
        """
        try:
            ret = dict()
            ret["entry_type"] = self.entry_type
            ret["key"] = self.key
            ret["fields"] = self.fields.to_dict()
            return ret
        except:
            return asdict(self)


@dataclass(repr=False)
class CitationFields:
    """A dataclass for citation fields; field names and types are taken from BibLaTeX.
    This class makes no attempt to format or represent the citation in any form
    other than as a dictionary. This class also does not perform any type-checking
    on fields, although it does create ``TypeAlias`` es for each field for the
    user's information. Please see the BibLaTeX or BibTeX documentation for a list of
    valid field names.
    """

    title: Literal = None
    """Title of the work, required for most bibliographies."""
    author: NameList = None
    """The author of a work. Typically, either `author` or `editor` is required."""
    editor: NameList = None
    """The editor of a work. Typically, either `author` or `editor` is required."""
    date: Date = None
    """The date the work was published. Typically, either `year` or `date` is required"""
    year: Literal = None
    """The year the work was published. Typically, either `year` or `date` is required."""
    journal: Literal = None
    """The journal an articles was published in. Both `journal` and `journaltitle` are accepted as field names."""
    journaltitle: Literal = None
    """The journal an articles was published in. Both `journal` and `journaltitle` are accepted as field names."""
    doi: Verbatim = None
    """The DOI identifier. Most works, and nearly all journal articles, have a DOI."""
    type: Key = None
    """The (sub)type of an :attr:`Citation.entry_type`. For example, "masters" for a masters thesis."""

    volume: int = None
    """The volume for a journal or multi-volume set. Use `volumes` to list the total number of volumes in a set."""
    number: Literal = None
    """The journal number within a volume, or a report number."""
    pages: Range = None
    """The pages for the work."""
    eid: Literal = None
    """The electronic identifier number, has replaced pages in some digital journals."""
    issue: Literal = None
    """The issue if the issue is not a number, for example, 'Spring'"""
    series: Literal = None
    """The series name, such as 'Chemical Reviews'"""
    part: Literal = None
    """The part, usually for reports or multi-volume sets."""

    eprint: Verbatim = None
    """Used for alternatives to DOI, such as PubMed PMIDs. The `eprintclass` and `eprinttype` fields identify the type of ID."""
    eprintclass: Literal = None
    eprinttype: Literal = None
    url: URI = None
    """A URL for access to a dataset or work. Use `urldate` to indicate when the URL was accessed."""
    urldate: Date = None
    """The date a `url` was accessed."""

    issuetitle: Literal = None
    booktitle: Literal = None
    eventtitle: Literal = None
    maintitle: Literal = None
    """The `maintitle`, `booktitle`, `eventtitle`, and `issuetitle` are used for containing works, such as for works within proceedings."""
    
    eventdate: Date = None
    
    institution: LiteralList = None
    organization: LiteralList = None
    publisher: LiteralList = None
    school: LiteralList = None

    location: LiteralList = None
    address: LiteralList = None
    venue: Literal = None

    abstract: Literal = None
    addendum: Literal = None
    afterword: NameList = None
    annotation: Literal = None
    annotator: NameList = None
    authortype: Key = None
    bookauthor: NameList = None
    bookpagination: Key = None
    chapter: Literal = None
    commentator: NameList = None
    edition: Union[int, Literal] = None
    editora: NameList = None
    editorb: NameList = None
    editorc: NameList = None
    editortype: Key = None
    editoratype: Key = None
    editorbtype: Key = None
    editorctype: Key = None
    entrysubtype: Literal = None
    file: Verbatim = None
    foreword: NameList = None
    holder: NameList = None
    howpublished: Literal = None
    introduction: NameList = None
    isan: Literal = None
    isbn: Literal = None
    ismn: Literal = None
    isrn: Literal = None
    issn: Literal = None
    iswc: Literal = None
    # Titles
    eventtitleaddon: Literal = None
    subtitle: Literal = None
    titleaddon: Literal = None
    journalsubtitle: Literal = None
    journaltitleaddon: Literal = None
    issuesubtitle: Literal = None
    issuetitleaddon: Literal = None
    booksubtitle: Literal = None
    booktitleaddon: Literal = None
    mainsubtitle: Literal = None
    maintitleaddon: Literal = None
    origtitle: Literal = None
    reprinttitle: Literal = None
    shorttitle: Literal = None
    shortjournal: Literal = None
    indextitle: Literal = None
    indexsorttitle: Literal = None
    sorttitle: Literal = None
    # Continued
    label: Literal = None
    language: KeyList = None
    library: Literal = None
    month: Literal = None
    nameaddon: Literal = None
    note: Literal = None
    origdate: Date = None
    origlanguage: KeyList = None
    origlocation: LiteralList = None
    origpublisher: LiteralList = None
    pagetotal: Literal = None
    pagination: Key = None
    pubstate: Key = None
    shortauthor: NameList = None
    shorteditor: NameList = None
    shorthand: Literal = None
    shorthandintro: Literal = None
    shortseries: Literal = None
    translator: NameList = None
    version: Literal = None
    volumes: int = None
    # SPECIAL FIELDS
    crossref: Key = None
    entryset: SeparatedValues = None
    execute: Special = None
    gender: Key = None
    langid: Key = None
    langidopts: Special = None
    ids: SeparatedValues = None
    keywords: SeparatedValues = None
    options: Special = None
    presort: Special = None
    related: SeparatedValues = None
    relatedoptions: SeparatedValues = None
    relatedtype: Special = None
    relatedstring: Literal = None
    sortkey: Literal = None
    sortname: NameList = None
    sortshorthand: Literal = None
    sortyear: int = None
    xdata: SeparatedValues = None
    xref: Key = None
    # FIELD ALIASES
    annote: Literal = None
    archiveprefix: Literal = None
    pdf: Verbatim = None
    primaryclass: Literal = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the citation.
        All blank (None) values will be removed from the dictionary
        so that it is minimal.

        Returns
        -------
        Dict[str, Any]
            minimal dictionary representation of the Citation
        """
        d = asdict(self)
        for k in list(d.keys()):
            if d[k] is None:
                del d[k]
        return d

    def __repr__(self) -> str:
        d = asdict(self)
        for k in list(d.keys()):
            if d[k] is None:
                del d[k]
        rep = str(self.__class__.__name__) + "("
        rep = rep + ", ".join(["{}={}".format(k, repr(v)) for k, v in d.items()])
        rep = rep + ")"
        return rep


def to_jsontypes(citations):
    """Convert a Citation, list of citations, or dictionary of citations to a JSON mapping.

    Parameters
    ----------
    citations : Citation, List[Citation], Any
        the citation(s) to convert

    Returns
    -------
    JSON valid object
        dictionary, list, or scalar
    """
    if isinstance(citations, str):
        return citations
    elif not isinstance(citations, list) and hasattr(citations, 'to_dict'):
        return citations.to_dict()
    elif is_dataclass(citations.__class__):
        return asdict(citations)
    elif isinstance(citations, (list, tuple)):
        ret = list()
        for obj in citations:
            ret.append(to_jsontypes(obj))
        return ret
    elif isinstance(citations, dict):
        ret = dict()
        for key, obj in citations.items():
            ret[key] = to_jsontypes(obj)
        return ret
    else:
        return str(citations)

def from_jsontypes(citations):
    """Convert a JSON mapping or list of mappings to a Citation structure.

    Parameters
    ----------
    citations : dict, list[dict]
        a dictionary or list of dictionaries to convert to Citation objects or leave as strings.

    Returns
    -------
    Any
        the converted objects
    """
    if isinstance(citations, list):
        ret = list()
        for obj in citations:
            ret.append(from_jsontypes(obj))
        return ret
    elif isinstance(citations, dict):
        try:
            ret = Citation(**citations)
        except:
            ret = dict()
            for key, obj in citations.items():
                ret[key] = from_jsontypes(citations)
        return ret
    elif isinstance(citations, str):
        return ret

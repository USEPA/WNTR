# coding: utf-8
"""Contains a dataclass that can be used to store citations.
"""
import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Union, List, TypeAlias, Tuple

Literal: TypeAlias = str
"""A literal string"""
Name: TypeAlias = str
"""A name string, preferrably in order without commas"""
NameList: TypeAlias = Union[Name, List[Name]]
"""A list of names, or a string with "and" between names"""
LiteralList: TypeAlias = Union[Literal, List[Literal]]
"""A list of literals, or a string with "and" between literals"""
Key: TypeAlias = str
"""A string that comes from a limited set of values"""
KeyList: TypeAlias = Union[Key, List[Key]]
"""A list of keys, or a string with "and" between keys"""
Verbatim: TypeAlias = str
"""A string that should not be interpreted (ie raw)"""
Special: TypeAlias = Any
"""Anything that isn't a string or list of strings"""
URI: TypeAlias = str
"""A valid URI"""
Date: TypeAlias = Union[str, datetime.date]
"""A date or string in yyyy-mm-dd format (must be 0-padded, eg 2021-02-02 for February 2, 2021"""
Range: TypeAlias = Union[str, Tuple[Any, Any]]
"""A 2-tuple of (start,stop) or a string with two values separated by '--' """
SeparatedValues: TypeAlias = Union[str, List[str]]
"""A list of strings, or a string that is delimited (the delimiter is not specified)"""

@dataclass(repr=False)
class CitationFields:
    """A dataclass for citations, most attribute names match biblatex names.
    This class makes no attempt to format or represent the citation in any form
    other than as a dictionary.

    Parameters
    ----------
    title: Literal
        The title is the only required field
    author: NameList, optional
    editor: NameList, optional
    date: Date, optional
    year: Literal, optional
    abstract: Literal, optional
    addendum: Literal, optional
    afterword: NameList, optional
    annotation: Literal, optional
    annotator: NameList, optional
    authortype: Key, optional
    bookauthor: NameList, optional
    bookpagination: Key, optional
    chapter: Literal, optional
    commentator: NameList, optional
    doi: Verbatim, optional
    edition: Union[int, Literal], optional
    editora: NameList, optional
    editorb: NameList, optional
    editorc: NameList, optional
    editortype: Key, optional
    editoratype: Key, optional
    editorbtype: Key, optional
    editorctype: Key, optional
    eid: Literal, optional
    entrysubtype: Literal, optional
    eprint: Verbatim, optional
    eprintclass: Literal, optional
    eprinttype: Literal, optional
    eventdate: Date, optional
    file: Verbatim, optional
    foreword: NameList, optional
    holder: NameList, optional
    howpublished: Literal, optional
    institution: LiteralList, optional
    introduction: NameList, optional
    isan: Literal, optional
    isbn: Literal, optional
    ismn: Literal, optional
    isrn: Literal, optional
    issn: Literal, optional
    issue: Literal, optional
    iswc: Literal, optional
    eventtitle: Literal, optional
    eventtitleaddon: Literal, optional
    subtitle: Literal, optional
    titleaddon: Literal, optional
    journalsubtitle: Literal, optional
    journaltitle: Literal, optional
    journaltitleaddon: Literal, optional
    issuesubtitle: Literal, optional
    issuetitle: Literal, optional
    issuetitleaddon: Literal, optional
    booksubtitle: Literal, optional
    booktitle: Literal, optional
    booktitleaddon: Literal, optional
    mainsubtitle: Literal, optional
    maintitle: Literal, optional
    maintitleaddon: Literal, optional
    origtitle: Literal, optional
    reprinttitle: Literal, optional
    shorttitle: Literal, optional
    shortjournal: Literal, optional
    indextitle: Literal, optional
    indexsorttitle: Literal, optional
    sorttitle: Literal, optional
    label: Literal, optional
    language: KeyList, optional
    library: Literal, optional
    location: LiteralList, optional
    month: Literal, optional
    nameaddon: Literal, optional
    note: Literal, optional
    number: Literal, optional
    organization: LiteralList, optional
    origdate: Date, optional
    origlanguage: KeyList, optional
    origlocation: LiteralList, optional
    origpublisher: LiteralList, optional
    pages: Range, optional
    pagetotal: Literal, optional
    pagination: Key, optional
    part: Literal, optional
    publisher: LiteralList, optional
    pubstate: Key, optional
    series: Literal, optional
    shortauthor: NameList, optional
    shorteditor: NameList, optional
    shorthand: Literal, optional
    shorthandintro: Literal, optional
    shortseries: Literal, optional
    translator: NameList, optional
    type: Key, optional
    url: URI, optional
    urldate: Date, optional
    venue: Literal, optional
    version: Literal, optional
    volume: int, optional
    volumes: int, optional
    crossref: Key, optional
    entryset: SeparatedValues, optional
    execute: Special, optional
    gender: Key, optional
    langid: Key, optional
    langidopts: Special, optional
    ids: SeparatedValues, optional
    keywords: SeparatedValues, optional
    options: Special, optional
    presort: Special, optional
    related: SeparatedValues, optional
    relatedoptions: SeparatedValues, optional
    relatedtype: Special, optional
    relatedstring: Literal, optional
    sortkey: Literal, optional
    sortname: NameList, optional
    sortshorthand: Literal, optional
    sortyear: int, optional
    xdata: SeparatedValues, optional
    xref: Key, optional
    address: LiteralList, optional
    annote: Literal, optional
    archiveprefix: Literal, optional
    journal: Literal, optional
    pdf: Verbatim, optional
    primaryclass: Literal, optional
    school: LiteralList, optional
    """
    title: Literal
    author: NameList = None
    editor: NameList = None
    date: Date = None
    year: Literal = None

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
    doi: Verbatim = None
    edition: Union[int, Literal] = None
    editora: NameList = None
    editorb: NameList = None
    editorc: NameList = None
    editortype: Key = None
    editoratype: Key = None
    editorbtype: Key = None
    editorctype: Key = None
    eid: Literal = None
    entrysubtype: Literal = None
    eprint: Verbatim = None
    eprintclass: Literal = None
    eprinttype: Literal = None
    eventdate: Date = None
    file: Verbatim = None
    foreword: NameList = None
    holder: NameList = None
    howpublished: Literal = None
    institution: LiteralList = None
    introduction: NameList = None
    isan: Literal = None
    isbn: Literal = None
    ismn: Literal = None
    isrn: Literal = None
    issn: Literal = None
    issue: Literal = None
    iswc: Literal = None
    # Titles
    eventtitle: Literal = None
    eventtitleaddon: Literal = None
    subtitle: Literal = None
    titleaddon: Literal = None
    journalsubtitle: Literal = None
    journaltitle: Literal = None
    journaltitleaddon: Literal = None
    issuesubtitle: Literal = None
    issuetitle: Literal = None
    issuetitleaddon: Literal = None
    booksubtitle: Literal = None
    booktitle: Literal = None
    booktitleaddon: Literal = None
    mainsubtitle: Literal = None
    maintitle: Literal = None
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
    location: LiteralList = None
    month: Literal = None
    nameaddon: Literal = None
    note: Literal = None
    number: Literal = None
    organization: LiteralList = None
    origdate: Date = None
    origlanguage: KeyList = None
    origlocation: LiteralList = None
    origpublisher: LiteralList = None
    pages: Range = None
    pagetotal: Literal = None
    pagination: Key = None
    part: Literal = None
    publisher: LiteralList = None
    pubstate: Key = None
    series: Literal = None
    shortauthor: NameList = None
    shorteditor: NameList = None
    shorthand: Literal = None
    shorthandintro: Literal = None
    shortseries: Literal = None
    translator: NameList = None
    type: Key = None
    url: URI = None
    urldate: Date = None
    venue: Literal = None
    version: Literal = None
    volume: int = None
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
    address: LiteralList = None
    annote: Literal = None
    archiveprefix: Literal = None
    journal: Literal = None
    pdf: Verbatim = None
    primaryclass: Literal = None
    school: LiteralList = None

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
        rep = str(self.__class__.__name__) + '('
        rep = rep + ', '.join(['{}={}'.format(k, repr(v)) for k, v in d.items()])
        rep = rep + ')'
        return rep
    

@dataclass(repr=False)
class Citation:
    """A class to hold a citation to document the source of a model.
    """
    entry_type: str
    key: str
    fields: CitationFields = field(default_factory=CitationFields)

    def __post_init__(self):
        if isinstance(self.fields, dict):
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
            ret['entry_type'] = self.entry_type
            ret['key'] = self.key
            ret['fields'] = self.fields.to_dict()
            return ret
        except:
            return asdict(self)

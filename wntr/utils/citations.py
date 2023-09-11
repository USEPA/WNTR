# coding: utf-8
"""Contains a dataclass that can be used to store citations.
Will output the class
"""
import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Union, List, TypeAlias, Tuple

Literal: TypeAlias = str
Name: TypeAlias = str
NameList: TypeAlias = Union[Name, List[Name]]
LiteralList: TypeAlias = Union[Literal, List[Literal]]
Key: TypeAlias = str
KeyList: TypeAlias = Union[Key, List[Key]]
Verbatim: TypeAlias = str
Special: TypeAlias = Any
URI: TypeAlias = str
Date: TypeAlias = Union[str, datetime.date]
Range: TypeAlias = Union[str, Tuple[Any, Any]]
SeparatedValues: TypeAlias = Union[str, List[str]]

@dataclass(repr=False)
class CitationFields:
    """A dataclass for citations, most attribute names match biblatex names.
    The exceptions are :attr:`entry_type`, which is the "@..." type of an entry
    :attr:`fulldate`, which is the "date" element of a bibliography entry
    and :attr:`reporttype`, which is the "type" element of a bib(la)tex entry.

    This class makes no attempt to format or represent the citation in any form
    other than as a dictionary.
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
            the citation dictionaries
        """
        try:
            ret = dict()
            ret['entry_type'] = self.entry_type
            ret['key'] = self.key
            ret['fields'] = self.fields.to_dict()
            return ret
        except:
            return asdict(self)

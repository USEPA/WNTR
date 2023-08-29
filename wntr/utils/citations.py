# coding: utf-8
"""Contains a dataclass that can be used to store citations.
Will output the class
"""
import datetime
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(repr=False)
class Citation:
    """A dataclass for citations, most attribute names match biblatex names.
    The exceptions are :attr:`citation_class`, which is the "@..." type of an entry,
    :attr:`fulldate`, which is the "date" element of a bibliography entry,
    and :attr:`report_type`, which is the "type" element of a bib(la)tex entry.

    This class makes no attempt to format or represent the citation in any form
    other than as a dictionary.
    """

    title: str
    year: int
    key: str = None
    author: str = None

    # citation type/subtype (e.g., "report"/"tech. rep.")
    citation_class: str = 'misc'
    report_type: str = None

    # document identifiers
    doi: str = None
    url: str = None
    isrn: str = None
    isbn: str = None
    issn: str = None
    eprint: str = None

    # container titles
    journaltitle: str = None
    maintitle: str = None
    booktitle: str = None
    issuetitle: str = None

    # conference/proceedings info
    eventtitle: str = None
    eventdate: datetime.date = None
    venue: str = None

    # publishing info
    institution: str = None
    organization: str = None
    publisher: str = None
    location: str = None
    howpublished: str = None
    language: str = None
    origlanguage: str = None

    # additional people
    editor: str = None
    bookauthor: str = None
    translator: str = None
    annotator: str = None
    commentator: str = None
    introduction: str = None
    foreword: str = None
    afterword: str = None

    # identifying info
    issue: str = None
    series: str = None
    volume: str = None
    number: str = None
    part: str = None
    edition: str = None
    version: str = None
    chapter: str = None
    pages: str = None
    volumes: str = None
    pagetotal: str = None

    # dates
    month: str = None
    fulldate: datetime.date = None
    urldate: datetime.date = None

    # extra
    note: str = None
    addendum: str = None
    abstract: str = None
    annotation: str = None

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
        rep = self(self.__class__.__name__) + '('
        rep = rep + ', '.join(['{}={}'.format(k, repr(v)) for k, v in d.items()])
        rep = rep + ')'
        return rep
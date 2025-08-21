# coding: utf-8

import argparse
import pathlib
import wntr


def wntr_convert(args=None):
    """Convert between WNTR input file formats. This is a command-line script.
    Use the command ``wntr-convert --help`` for details.

    File formats are determined from the filename extension. E.g., using the command
        
    ``wntr-convert myfile.inp myfile.json`` 
        
    will convert an EPANET INP-formatted file into a WNTR JSON-formatted file.

    Parameters
    ----------
    args : Namespace
        An :class:``argparse.Namespace`` object that can be called instead of reading
        from the command line. Generally not used.
    """
    parser = argparse.ArgumentParser(
        description="""Convert between WNTR input file formats.
        File formats are determined from the filename extension. E.g., using the command
        
        ``wntr-convert myfile.inp myfile.json`` 
        
        will convert an EPANET INP-formatted file into a WNTR JSON-formatted file."""
    )
    parser.add_argument("infile", help="Name of the file to convert.")
    parser.add_argument("outfile", help="Name of the file to create.")
    args = parser.parse_args(args)
    infile = pathlib.Path(args.infile)
    outfile = pathlib.Path(args.outfile)
    try:
        if not infile.exists():
            parser.error(f'The file "{infile}" does not exist.')
        if not outfile.parent.exists() and not outfile.parent.is_dir():
            parser.error(
                f'The path "{outfile.parent}" does not exist or is not a directory.'
            )
        match infile.suffix.lower():
            case ".inp":
                wn = wntr.network.io.read_inpfile(str(infile))
            case ".json":
                wn = wntr.network.io.read_json(str(infile))
            case _:
                parser.error(
                    f'Unknown file format "{infile.suffix}": expected one of ".inp", ".json"'
                )
        match outfile.suffix.lower():
            case ".inp":
                wntr.network.io.write_inpfile(wn, str(outfile))
            case ".json":
                wntr.network.io.write_json(wn, str(outfile), indent=2)
            case _:
                parser.error(
                    f'Unknown file format "{outfile.suffix}": expected one of ".inp", ".json"'
                )
    except IOError as e:
        parser.error(str(e))
    except Exception as e:
        parser.error(str(e))


if __name__ == "__main__":
    wntr_convert()

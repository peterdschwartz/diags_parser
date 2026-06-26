import argparse
import textwrap
from diags_parser.my_types import LineTuple, LogicalLineIterator
from diags_parser.parser import Parser
from diags_parser.tracing import Trace
from diags_parser.registry import SUPPORTED
from pathlib import Path

def parse_line(args):
    if args.line:
        lines: list[str] = args.line.split('\n')
    elif args.file:
        path = Path(args.file)
        assert path.exists()
        with path.open('r') as input:
            lines = input.readlines()

    line_tups = [LineTuple(ln=i,line=line) for i,line in enumerate(lines)]
    parser = Parser(lines=line_tups)

    Trace.enabled = args.trace

    program = parser.parse_program()
    from pprint import pprint
    print("\n ----- Grouped String -----")
    for stmt in program.statements:
        print(str(stmt))

    print("\n ---- AST to Dictionary -----")

    for stmt in program.statements:
        pprint(stmt.to_dict())
    return

def list_supported_functions(args):
    from pprint import pprint
    print('\n'.join([str(f) for f in SUPPORTED]))
    return

def main():
    desc = textwrap.dedent("""
    E3SM Diags Parser (edp) 
    """)
    _arg_parser = argparse.ArgumentParser(prog="edp",description=desc)
    _subparser = _arg_parser.add_subparsers(dest="command", required=True)

    _parse_parser = _subparser.add_parser("parse", help="Parse provided string")
    _parse_parser.add_argument("-s",required=False,dest="line")
    _parse_parser.add_argument("-f",required=False,dest="file",help="parse entire file")
    _parse_parser.add_argument("-t",required=False,dest="trace",action="store_true",help="Enable Tracing of recurisve functions")
    _parse_parser.set_defaults(func=parse_line)

    _func_parser = _subparser.add_parser("functions",help="List supported functions")
    _func_parser.set_defaults(func=list_supported_functions)

    args = _arg_parser.parse_args()
    args.func(args)

    return

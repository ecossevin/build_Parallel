import sys
from pathlib import Path
import re
import pickle
import click

from loki import *
from transformations.parallel_routine_dispatch import ParallelRoutineDispatchTransformation

import logical
import logical_lst



def bprint(string, size=45, t="star", edge=3):
    """
    Print ***********************
          ***      string     ***
          ***********************
    :param string: string to print
    :param size: size of the "****************" line
    :param t: symbole the line is made of
    :param edge: size of the edge, here 3: "***"
    """
    l = len(string)
    e = (size - l) // 2
    r = (size - l) % 2
    if t == "star":
        tt = "*"
    print(tt * size)
    print(tt * edge + " " * (e - edge) + string + " " * (e - edge + r) + tt * edge)
    print(tt * size)

@click.command()
# @click.option('--pathr', help='path of the file to open')
# @click.option('--pathw', help='path of the file to write to')
@click.option("--pathpack", help="absolute path to the pack")
@click.option("--pathview", help="path to src/local/... or src/main/...")
@click.option("--pathfile", help="path to the file, with the file name in the path")
@click.option(
    "--horizontal_opt", default=None, help="additionnal possible horizontal idx"
)
@click.option(
    "--inlined",
    "-in",
    default=None,
    multiple=True,
    help="names of the routine to inline",
)
def parallel_trans(pathpack, pathview, pathfile, horizontal_opt, inlined):
    global map_variables

    # ----------------------------------------------
    # setup
    # ----------------------------------------------
    verbose = True
    # verbose=False
    intent = False
    if verbose :print("pathpack =", pathpack)
    if verbose :print("pathview =", pathview)
    if verbose :print("pathfile =", pathfile)

    pathr = pathpack + "/" + pathview + pathfile

    pathw = pathr.replace(".F90", "") + "_parallel.F90"
    pathw = pathw.replace("main", "local") 

    if verbose:
        print("pathr=", pathr)
    if verbose:
        print("pathw=", pathw)
    source = Sourcefile.from_file(pathr)

    item = ProcedureItem(name='parallel_routine_dispatch', source=source)
    routine = source.subroutines[0]
    
    is_intent = False 
    horizontal = [
            "KLON", "YDCPG_OPTS%KLON", "YDGEOMETRY%YRDIM%NPROMA",
            "KPROMA", "YDDIM%NPROMA", "NPROMA"
    ]
    path_map_index = "/home/gmap/mrpm/cossevine/build_Parallel/src/field_index_new.pkl"
    breakpoint()
    transformation = ParallelRoutineDispatchTransformation(is_intent, horizontal, path_map_index)
    true_symbols, false_symbols = logical_lst.symbols()

    # ----------------------------------------------
    # transformation:
    # ----------------------------------------------
    resolve_associates(routine)
    logical.transform_subroutine(routine, true_symbols, false_symbols)
    transformation.apply(routine, item=item)
#    sanitise_imports(routine)


#    calls = [call for call in FindNodes(CallStatement).visit(routine.body)]
#    interface = [imp for imp in FindNodes(Imports).visit(routine.spec) if imp.c_import]
#    dcls = get_dcls(
#        routine, lst_horizontal_size
#    )  # one dcl per line + return lst of array dcl
#    regions = GetPragmaRegionInRoutine(routine)
#    PragmaRegions = FindNodes(PragmaRegion).visit(routine.body)

#    subname = routine.name

#        if intent:
#            read_interface(
#            calls, path_interface, map_intent, map_region_intent
#        )  # create map_intent[calls]
#        # exit(1)
#        if verbose:
#            print("Interface map_intent =", map_intent)
#            print("Interface map_region_intent =", map_region_intent)

    Sourcefile.to_file(fgen(routine, linewidth=128), Path(pathw))


# *********************************************************
# *********************************************************
# *********************************************************
#       Calling  the       transformation
# *********************************************************
# *********************************************************
# *********************************************************

parallel_trans()
# namearg=sys.argv[1]
# namearg=namearg.replace(".F90", "")
# Sourcefile.to_file(source.to_fortran(), Path(namearg+"_out.F90"))

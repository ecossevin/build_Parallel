import sys
from pathlib import Path
import re
import pickle
import click

from loki import *
from transformations.parallel_routine_dispatch import ParallelRoutineDispatchTransformation

import logical
import logical_lst
from preprocess import get_preprocess_pragma

def init_path(pathpack, pathview, pathfile, horizontal_opt, inlined):
    verbose = True
    if verbose :print("pathpack =", pathpack)
    if verbose :print("pathview =", pathview)
    if verbose :print("pathfile =", pathfile)

    pathr = pathpack + "/" + pathview + pathfile

    pathw = pathr.replace(".F90", "") + "_parallel.F90"
    pathw = pathw.replace("main", "local") 
    pathw = pathw.replace("test/src", "test/loki")


    if verbose:
        print("pathr=", pathr)
    if verbose:
        print("pathw=", pathw)
    return(pathr, pathw)

def call_parallel_trans(pathpack, pathview, pathfile, horizontal_opt, inlined):
    pathr, pathw = init_path(pathpack, pathview, pathfile, horizontal_opt, inlined)
    parallel_trans(pathr, pathw)

def parallel_trans(pathr, pathw):
    global map_variables

    # ----------------------------------------------
    # setup
    # ----------------------------------------------
    verbose = True
    # verbose=False
    intent = False
    preprocess_pragma = True

    if preprocess_pragma: #change acdc pragma into loki pragma with end keyword
        lines = get_preprocess_pragma(pathr)
        lines = ''.join(lines)
        source = Sourcefile.from_source(lines)
    else:
        source = Sourcefile.from_file(pathr)

    item = ProcedureItem(name='parallel_routine_dispatch', source=source)
    routine = source.subroutines[0]
    
    is_intent = False 
    horizontal = [
            "KLON", "YDCPG_OPTS%KLON", "YDGEOMETRY%YRDIM%NPROMA",
            "KPROMA", "YDDIM%NPROMA", "NPROMA"
    ]
    path_map_index = "/home/gmap/mrpm/cossevine/build_Parallel/src/field_index_new.pkl"
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




def call_parallel_trans_dbg():
    #src_file = "src/arpege/apl_arpege_bench.F90"
    src_file = "src/arpege/apl_arpege_bench_loki.F90"
    pathr = src_file 
    pathw = "src/arpege/out.F90"
    parallel_trans(pathr, pathw)



if __name__ == "__main__":
    call_parallel_trans_dbg()

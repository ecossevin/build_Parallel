from loki import Sourcefile, ProcedureItem, fgen
from pathlib import Path
from loki import resolve_associates
from transformations.parallel_routine_dispatch import ParallelRoutineDispatchTransformation
import sys 

import logical
import logical_lst

def process(src_file, src_name):
    source = Sourcefile.from_file(src_file)
    item = ProcedureItem(name='parallel_routine_dispatch', source=source)
    routine = source[src_name]
    
    is_intent = False 
    horizontal = [
            "KLON", "YDCPG_OPTS%KLON", "YDGEOMETRY%YRDIM%NPROMA",
            "KPROMA", "YDDIM%NPROMA", "NPROMA"
    ]
    path_map_index = "/home/gmap/mrpm/cossevine/build_Parallel/field_index_new.pkl"
    transformation = ParallelRoutineDispatchTransformation(is_intent, horizontal, path_map_index)
    true_symbols, false_symbols = logical_lst.symbols()

    resolve_associates(routine)
    logical.transform_subroutine(routine, true_symbols, false_symbols)
    transformation.apply(routine, item=item)
    #transformation.apply(source[src_name], item=item)
    Sourcefile.to_file(fgen(routine, linewidth=128), Path("src/arpege/out.F90"))
#    breakpoint()

src_file = "src/arpege/apl_arpege_bench_loki.F90"
#src_file = "src/apl_arpege_loki2.F90"
src_name = 'apl_arpege'

#src_file = "src/dispatch_routine2.F90"
#src_file = "src/dispatch_routine.F90"
#src_name = "DISPATCH_ROUTINE"

process(src_file, src_name)



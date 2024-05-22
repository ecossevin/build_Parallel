from loki import Sourcefile, ProcedureItem, fgen
from pathlib import Path
from loki import resolve_associates
from transformations.parallel_routine_dispatch import ParallelRoutineDispatchTransformation

def process(src_file, src_name):
    source = Sourcefile.from_file(src_file)
    item = ProcedureItem(name='parallel_routine_dispatch', source=source)
    routine = source[src_name]
    
    is_intent = False 
    horizontal = [
            "KLON", "YDCPG_OPTS%KLON", "YDGEOMETRY%YRDIM%NPROMA",
            "KPROMA", "YDDIM%NPROMA", "NPROMA"
    ]
    path_map_index = "/field_index_new.pkl"
    transformation = ParallelRoutineDispatchTransformation(is_intent, horizontal, path_map_index)

    resolve_associates(routine)
    transformation.apply(routine, item=item)
    #transformation.apply(source[src_name], item=item)
    Sourcefile.to_file(fgen(routine), Path("src/out.F90"))
#    breakpoint()

src_file = "src/apl_arpege_loki.F90"
src_name = 'apl_arpege'

#src_file = "src/dispatch_routine2.F90"
#src_file = "src/dispatch_routine.F90"
#src_name = "DISPATCH_ROUTINE"
process(src_file, src_name)



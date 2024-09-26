import sys
from loki import *
from pathlib import Path
import re


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



def InsertPragmaRegionInSources(sources):
    routines = sources.routines
    for routine in routines:
        InsertPragmaRegionInRoutine(routine)


def InsertPragmaRegionInRoutine(routine):
    start = None
    for pragma in FindNodes(Pragma).visit(routine.body):
        if pragma.keyword == "ACDC":
            if "{" in pragma.content:
                start = pragma
            elif "}" in pragma.content:
                if not start:
                    print("ACDC } without previous {")
                else:
                    # Create a PragmaRegion object from the two pragma
                    # (See pragma_utils.py)
                    # This is a destructive operation !
                    extract_pragma_region(routine.body, start=start, end=pragma)
                    start = None
        else:
            print("Unknown pragma found : {pragma}")


def GetPragmaRegionInRoutine(routine):
    """
    Insert pragma region in the code. And returns a dict with the content of the ACDC pragma.
    """
    InsertPragmaRegionInRoutine(routine)
    pragma_regions = []
    for region in FindNodes(PragmaRegion).visit(routine.body):
        re_name = re.compile("NAME=(\w+)")
        re_name = re_name.search(region.pragma.content)
        if re_name:
            name = re_name[1]
        else:
            name = None
        re_targets = re.compile("TARGET=([^,]+)")
        re_targets = re_targets.search(region.pragma.content)
        if re_targets:
            targets = re_targets[1]
            targets = targets.split("/")
        else:
            targets = ["OpenMP", "OpenMPSingleColumn", "OpenACCSingleColumn"]
        # region.prepend(Comment(text="Début région"))
        # region.append(Comment(text="Fin région"))
        # print(fgen(region))
        pragma_regions.append({"region": region, "targets": targets, "name": name})
    return pragma_regions



def read_interface(calls, path_interface, map_intent, map_region_intent):
    """
    map_intent[nom_routine] = [nom : intent]
    """
    #    verbose=False
    verbose = True
    #   nb_iter = 0
    debug = True  # read interface in /src
    # debug = False #read in real repo
    for call in calls:
        # ============================================
        #!!! Limitation if the names are different from one call to another !!!

        # CALL A(B) -> map_intent[A][B] = intent(xxx)
        # CALL A(D) -> map_intent[A][D] won't be defined
        if call not in map_intent:
            # ============================================
            if verbose:
                print("call =", call.name.name)
            call_name = str(call.name.name.lower())
            call_name = call_name.replace(
                "_openacc", ""
            )  # _openacc interfaces and regular interfaces are regular interfaces
            map_intent[call_name] = {}
            #            call_path = map_path[call_name+'.F90']
            call_path = path_interface + "/" + call_name + ".intfb.h"
            #            call_path=call_path.replace(".F90",".intfb.h")
            if debug:
                call_path = (
                    "/home/cossevine/build_Parallel/"
                    + "src/"
                    + call_name
                    + ".intfb.h"
                )
            if verbose:
                print("call_path =", call_path)
                print("call_name=", call_name)
            #            exit(1)
            with open(call_path) as f:
                lines = f.readlines()
            lines = lines[1:-1]  # rm INTERFACE and END INTERFACE from the routine...
            content_call = "".join(lines)
            call_source = Sourcefile.from_source(content_call)
            call_ir = call_source[call_name.upper()]
            if verbose:
                print("call_ir =", fgen(call_ir))
            for arg_idx in range(len(call_ir.arguments)):
                arg = call.arguments[arg_idx]
                if not (
                    isinstance(arg, symbols.LogicalOr)
                    or isinstance(arg, symbols.LogicalAnd)
                ):
                    #                    arg_name=call.arguments[arg_idx].name #names in the caller
                    arg_name = arg.name  # names in the caller
                    arg_ = call_ir.arguments[arg_idx]
                    map_intent[call_name][arg_name] = arg_.type.intent
                    #                    if nb_iter == 0:
                    #                        map_region_intent[arg_name] = map_intent[call_name][arg_name]
                    #                    else:
                    if arg_name not in map_region_intent:
                        map_region_intent[arg_name] = map_intent[call_name][arg_name]
                    else:
                        map_region_intent[arg_name] = analyse_intent(
                            map_intent[call_name][arg_name], map_region_intent[arg_name]
                        )  # comparing intent of the arg in the region with the intent of the arg in the call
        #            nb_iter = nb_iter+1
        print("map_region_intent =", map_region_intent)


def analyse_intent(intent1, intent2):
    if intent1 or intent2 == "out":
        return "out"
    elif intent1 or intent2 == "inout":
        return "inout"
    elif intent1 and intent2 == "in":
        return "in"


##*********************************************************
##             Creating lst of dim for derive types
##*********************************************************
##print(map_field)
##f=open("map_field.txt", "x")
##f.write(map_field)
#
##with open('map_field.txt', 'w') as
##*********************************************************
##*********************************************************

#path_irgrip = "/home/gmap/mrpm/cossevine/kilo/src/acdc/loki"
path_irgrip = "/home/cossevine/kilo/src/acdc/loki"
sys.path.append(path_irgrip)
import irgrip

import logical
import logical_lst
import pickle

import click


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
    print("pathpack =", pathpack)
    print("pathview =", pathview)
    print("pathfile =", pathfile)

    pathr = pathpack + "/" + pathview + pathfile

    pathw = pathr.replace(".F90", "") + "_parallel"

    if verbose:
        print("pathr=", pathr)
    if verbose:
        print("pathw=", pathw)
        ###    horizontal=Dimension(name='horizontal',size='KLON',index='JLON',bounds=['KIDIA','KFDIA'],aliases=['NPROMA','KDIM%KLON','D%INIT'])
        ###    vertical=Dimension(name='vertical',size='KLEV',index='JLEV')
        ###
        ###     #lst_horizontal_idx=['JLON','JROF','JL']
        ###    lst_horizontal_idx=['JLON','JROF']
        ###    #the JL idx have to be added only when it's used at an horizontal idx, because it's used as avertical idx in some places.... this should be fixed... The transformation script could check wether JL is a hor or vert idx instead of adding JL to the lst_horizontal_idx conditionally.
        ###    if horizontal_opt is not None:
        ###        lst_horizontal_idx.append(horizontal_opt)
        ###    if verbose: print("lst_horizontal_idx=",lst_horizontal_idx)
        ###
        ###    lst_horizontal_size=["KLON","YDCPG_OPTS%KLON","YDGEOMETRY%YRDIM%NPROMA","KPROMA", "YDDIM%NPROMA", "NPROMA"]
        ###    lst_horizontal_bounds=[["KIDIA", "YDCPG_BNDS%KIDIA","KST"],["KFDIA", "YDCPG_BNDS%KFDIA","KEND"]]
        ###
        ###    true_symbols, false_symbols=logical_lst.symbols()
        ###    false_symbols.append('LHOOK')

    source = Sourcefile.from_file(pathr)
    true_symbols, false_symbols = logical_lst.symbols()
    # false_symbols.append('LHOOK')


    # ==========================================================
    # Loading the index file
    # ==========================================================
    with open(pathpack + "/" + "field_index.pkl", "rb") as fp:
        field_index = pickle.load(fp)

    # ==========================================================
    # Creating the map_path
    # ==========================================================
    #    from call_path import map_path
    #    path_acc = '/src/local/ifsaux/openacc'
    #    map_path_old=copy.deepcopy(map_path)
    #    for path in map_path_old:
    #       # new_name=path.replace('.F90','_openacc.F90')
    #       # map_path[new_name]=path_acc+'/'+map_path[path].replace('.F90','_openacc.F90') #creating path for _openacc.F90 files
    #       # map_path[path]=pathpack+'/'+pathview+map_path[path]
    #       # map_path[new_name]=pathpack+map_path[new_name]
    #       map_path[path]=pathpack+'/'+pathview+".intfb/arpifs"+"/"+path
    #       if verbose: print("map_path =", map_path[path])
    #
    #
    #    if verbose: print(map_path)

    path_interface = pathpack + "/" + pathview + ".intfb/arpifs"
    map_intent = {}
    map_dim = [{}, {}]  # map_dim[old_field]=new_field(:,:,;...)
    lst_derive_type = []  # store derive types that are added to the routine spec

    # ----------------------------------------------
    # transformation:
    # ----------------------------------------------

    logical.transform_subroutine(routine, true_symbols, false_symbols)
    resolve_associates(routine)

    dcls = get_dcls(
        routine, lst_horizontal_size
    )  # one dcl per line + return lst of array dcl
    regions = GetPragmaRegionInRoutine(routine)
    PragmaRegions = FindNodes(PragmaRegion).visit(routine.body)

    subname = routine.name

    if intent:
        read_interface(
        calls, path_interface, map_intent, map_region_intent
    )  # create map_intent[calls]
    # exit(1)
    if verbose:
        print("Interface map_intent =", map_intent)
        print("Interface map_region_intent =", map_region_intent)

    args = FindVariables(unique=True).visit(region)
    Sourcefile.to_file(fgen(routine), Path(pathw + "_loki.F90"))


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

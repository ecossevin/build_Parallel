import sys
from loki import *
from pathlib import Path
import re
import json

def get_dcls(routine, lst_horizontal_size):
    """
    
    """

#    verbose=False
    verbose=True

    dcls={}
    variable_map=routine.variable_map
    decls_map={}
    for decl in FindNodes(VariableDeclaration).visit(routine.spec):
        new_decls=()
        for s in decl.symbols:
            new_decl=decl.clone(symbols=(s,))
            new_decls=new_decls+(new_decl,)
            if isinstance(s, symbols.Array):
                if (s.dimensions[0] in lst_horizontal_size): #store all NPROMA arrays
                    
                    dcls[s.name]=new_decl #map to find var decl when changing it
        decls_map[decl]=new_decls
    routine.spec=Transformer(decls_map).visit(routine.spec)
#    if verbose: print("dcls= ", dcls)   
#    dcls[s.name]=decls
    return(dcls) #dcls map : var.name : var.declaration 

def change_arrays(routine, dcls, lst_horizontal_size, map_dim):
    """
    Changes NPROMA arrays into field api objects.
    :param dcls: dict of NRPOMA arrays declarations to change.
    """
#*******        ****************************************************
                        #2) LOCAL ARGS of the caller
                        #local var Z => PT, Z
                        #build an array with the name of the arrays that were changed, replace the arrays gradually
#*******        ************************************************
    verbose=False
    #verbose=True
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',0,ZHOOK_HANDLE_FIELD_API)")
    field_new_lst=()
    field_new_lst=field_new_lst+new_node
    for dcl in dcls:
        var_dcl=dcls[dcl]
        var=var_dcl.symbols[0]
        var_routine=var
        d = len(var.dimensions)+1 #FIELD_{d}RB
        dd = d*":,"
        dd = dd[:-1]
        #map_dim[var.name]="YL_"+var_routine.name+dd
        map_dim[var.name]="YL_"+var_routine.name+"("+dd+")"
        #map_dim[var.name]=var_routine.name+dd
        str_node1=f"CLASS (FIELD_{d}RB), POINTER :: YL_{var_routine.name}"
        new_var1=irgrip.slurp_any_code(str_node1)
        if var_routine.type.kind:
                                   
            str_node2=f"{var_routine.type.dtype.name} (KIND={var_routine.type.kind.name}), POINTER :: {var_routine.name} ({dd})"
                      #         var_routine.type.dtype.name     var.type.kind.name
        else:
            str_node2=f"{var_routine.type.dtype.name}, POINTER :: {var_routine.name} ({dd})"
            new_var2=irgrip.slurp_any_code(str_node2)
        new_var2=irgrip.slurp_any_code(str_node2)
        routine.spec=irgrip.insert_at_node(var_dcl, (new_var1, new_var2) , rootnode=routine.spec)
        ubound="["
        lbound="["
        zero=True #if true, means that lbound=only zero
        for dim in var_routine.dimensions:
            new_dim=False
            is_lbound=False
            regex="(.*):(.*)"
            str_dim=fgen(dim)
            new_dim=re.match(regex, str_dim)
            if verbose: print("str_dim= ", str_dim) 
            if new_dim:
                if verbose: print("new_dim= ", new_dim) 
                is_lbound=True
                ubound=ubound+new_dim.group(2)+", "
                lbound=lbound+new_dim.group(1)+", "
            else:
                ubound=ubound+str_dim+", "
                #ubound=ubound+new_dim+", "
                lbound=lbound+"0, "
 
        ubound=ubound[:-2]+']' #rm last coma and space
        lbound=lbound[:-2]+']' #rm last coma and space
        if not is_lbound:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, PERSISTENT=.TRUE.)"
        else:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, LBOUNDS={lbound}, PERSISTENT=.TRUE.)"
        if verbose: print("field_str= ", field_str) 
        field_node=irgrip.slurp_any_code(field_str)
        #field_new_lst.append(field_node)
        field_new_lst=field_new_lst+field_node
        #field_lst.append(field_node)
        
                
    #change NPROMA array name in the routine body  => NO 
    ##########variable_map={}
    ##########for var in FindVariables().visit(routine.body):
    ##########    if var.name in dcls:
    ##########        variable_map[var]=var.clone(name="YL_"+var.name) 
    ##########routine.body = SubstituteExpressions(variable_map).visit(routine.body)
  
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',1,ZHOOK_HANDLE_FIELD_API)")
    field_new_lst+new_node
    routine.body.insert(1, field_new_lst) #insert at 1 => after first LHOOK 
       

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
            targets = ['OpenMP','OpenMPSingleColumn','OpenACCSingleColumn']
    	# region.prepend(Comment(text="Début région"))
    	# region.append(Comment(text="Fin région"))
    	# print(fgen(region))
        pragma_regions.append({"region": region, "targets": targets, "name": name})
    return pragma_regions
    

def generate_openmp(routine, calls, map_dim, call_arrays):
    """
    :param map_dim: map_dim[old_var]=new_var(:,:,...
    """
    str_openmp=()
    str_openmp=f"IF (LPARALLELMETHOD ('OPENMP','{subname}:{name}')) THEN\n"
    str_data=generate_get_data(call_arrays, "HOST", "GET_DATA")
    str_openmp=str_openmp+str_data
    strhook=f"{subname}:{name}:COMPUTE"
    hookcode=lhook(strhook,"0", "COMPUTE")
    str_openmp=str_openmp+hookcode
    code="CALL YLCPG_BNDS%INIT (YDCPG_OPTS)\n"
    str_openmp=str_openmp+code 
    if call_scalar:
        private="JBLK,"+",".join(call_scalar)
    else:
        private="JBLK"
    firstprivate="YLCPG_BNDS"
    code="!$OMP PARALLEL DO PRIVATE ({private}) FIRSTPRIVATE({firstprivate})\n"
    str_openmp=str_openmp+code 
    code="DO JBLK = 1, YDCPG_OPTS%KGPBLKS\n"
    str_openmp=str_openmp+code
    code="CALL YLCPG_BNDS%UPDATE (JBLK)\n"
    str_openmp=str_openmp+code
    # =================================================
    #TODO: IF MORE THAN ONE CALL
#    for call in cals:
    call=calls[0]
    # =================================================
    str_call=fgen(call)
    print("str_call = ",  str_call)
    print("map_dim = ", map_dim)
    file1=open("myfile.txt", "w")
    file1.write(json.dumps(map_dim))
    file1.close()
    for arg in call.arguments:
        print("arg = ", arg.name)
        print("type_arg = ", type(arg.name))
       
        if arg.name in map_dim:
            print("************** IN MAP DIM*************************")
            print("arg = ", arg.name)
            print("map = ", map_dim[arg.name])
            str_call=str_call.replace(arg.name+",", map_dim[arg.name]+",")
    str_call=str_call.replace(":)","JBLK)")
    print(str_call)
    str_openmp=str_openmp+str_call
    hookcode=lhook(strhook,"1", "COMPUTE")
    str_openmp=str_openmp+hookcode 
    strifsync=f"IF (LSYNCHOST ('{subname}:{name}')) THEN\n"
    str_openmp=str_openmp+strifsync
    strsynchost=generate_get_data(call_arrays, "HOST", "SYNCHOST")
    str_openmp=str_openmp+strsynchost
    strifsync="ENDIF\n"
    str_openmp=str_openmp+strifsync
    str_null=generate_null(call_arrays, subname, name)
    str_openmp=str_openmp+str_null
#    str_openmp=str_openmp+"ENDIF\n"   #=> ENDIF must be removed by next compute area of the current region.  
    return(str_openmp)  
    
ignore_list = [
        "YDCPG_BNDS%KIDIA",
        "YDCPG_BNDS%KFDIA",
        "YDGEOMETRY",
        "YDMODEL",
       ]
#def gen_omp_target(subname, name, args_caller, args_callee, local_ptr_to_field_api):
#   	s = f"    IF (LPARALLELMETHOD ('OPENMP','{subname}:{name}')) THEN\n"
#    s += f"    IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:GET_DATA',0,ZHOOK_HANDLE_FIELD_API)\n"
#   
#    for arg_caller, arg_callee in zip(args_caller, args_callee):
#   	    newname = arg_caller.name.replace("%", "_")
#	intent = arg_callee.type.intent
#	if arg_callee.name in ignore_list:
#		continue
#	ptr = "Z_" + newname
#	target = arg_caller.name
#
#	if arg_caller.name in local_ptr_to_field_api:
#		ptr = arg_caller.name
#	    target = "YL_" + arg_caller.name
#
#	if intent == "in":
#		s += f"    {ptr} => GET_HOST_DATA_RDONLY ({target})\n"
#	elif intent == "out" or intent == "inout":
#		s += f"    {ptr} => GET_HOST_DATA_RDWR ({target})\n"
#	else:
#		print("Unknown intent")
#	    sys.exit(-1)
#    s += f"IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:GET_DATA',1,ZHOOK_HANDLE_FIELD_API)\n"
#    return s

#
#def get_subs_called(reg):
#    return [call for call in FindNodes(CallStatement).visit(reg)]
#

#def get_callee_args_of(subname):
#	filename = "src/" + str(subname).lower() + ".F90"
#    file = Sourcefile.from_file(filename)
#    args_callee = []
#    if len(file.routines) > 1:
#	    raise Except("Multiple routines in a file is not handled")
#    for sub in file.routines:
#	    for v in sub.arguments:
#		    args_callee.append(v)
#    return args_callee


def get_args_decl(subname):
    filename = "src/" + str(subname).lower() + ".F90"
    file = Sourcefile.from_file(filename)
    print(type(file.routines[0].arguments[0]))
    print(file.routines[0].arguments[0])
    return file.routines[0].arguments


def contains_ignore(typename):
#    contain = ["GEOMETRY", "CPG_BNDS_TYPE", "CPG_OPTS_TYPE", "CPG_MISC_TYPE", "CPG_GPAR_TYPE", "CPG_PHY_TYPE", "MF_PHYS_TYPE", "MF_PHYS_SURF_TYPE", "CPG_SL2_TYPE", "FIELD_VARIABLES", "MODEL", "TYP_DDH"]
    contains_ignore = ["MODEL", "GEOMETRY", "CPG_BNDS_TYPE", "CPG_OPTS_TYPE"]
    return (typename.upper() in contains_ignore)


def contains_field_api_member(typename):
    containg_field_api = [
        "FIELD_VARIABLES",
        "CPG_DYN_TYPE",
        "CPG_PHY_TYPE",
        ]
    return (typename.upper() in containg_field_api)



def compute_call(routine, call, field_index, call_arrays, call_scalar, lst_derive_type, map_dim, lst_horizontal_size):
    """
    :param routine:.
    :param field_index: index of field api struct members 
    :param call_arrays: mapping of names. call_arrays[Z_...]=YL_Z...; call_arrays[Z_A_B_C...]=A%B%C
    :param call_scalar
    :param ???
    :param lst_derive_type: lst of derived type that were already added to the routine spec
#######    :param dcls: maps the derive type name with its declaration in order to insert new dcl node at theright place
    """
    for arg in call.arguments:
        print("arg = ",  arg)
        #arg can be logical and/or: "YDCPG_OPTS%YRSURF_DIMS%YSD_VVD%NUMFLDS>=8.AND.YDMODEL%YRML_PHY_MF%YRPHY"
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            arg_name=arg.name
            if '%' in arg_name: # 1) derive_type already on lst_derive_type, 2) derive_type in index, 3) derive_type CPG_OPTS_TYPE 
                arg_basename=arg_name.split("%")[0]
                var_routine=routine.variable_map[arg_basename]
                arg_name_=arg_name_='%'.join(arg_name.split("%")[1:])
#                print("var_routine = ", var_routine)
#                print("var_routine.type.dtype = ", var_routine.type.dtype)
#                print("type(var_routine.type.dtype) = ", type(var_routine.type.dtype))
                if arg_name in lst_derive_type: #1) derive_type already on lst_derive_type
                    new_name="Z_"+arg_name.replace("%","_")
                    call_arrays[new_name]=arg_name
                    print(" ************ 1 adding var to call_attays   ****************") 
                    print("arg_name= ",  arg_name)
                    print("new_name  = ",  new_name)
                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                elif (var_routine.type.dtype.name+"%"+arg_name_ in field_index): #2) derive_type in index 
                #elif arg_name in var_routine.type.dtype.name+"%"+arg_name_ in field_index: #2) derive_type in index 
                    new_name="Z_"+arg_name.replace("%","_")
                    call_arrays[new_name]=arg_name
                    print(" ************ 2 adding var to call_attays   ****************") 
                    print("arg_name= ",  arg_name)
                    print("new_name",  new_name)

                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                    lst_derive_type.append(arg_name)
                    key=var_routine.type.dtype.name+'%'+arg_name_
                    new_var_type = field_index[key][0] 
                    d=field_index[key][1][:-1]+",:)"
                    dd=re.match("([A-Z0-9]*)(.*)", d)
                    new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+d  #A%B%C => A%B%C(:,:,:)
                    map_dim[arg_name]=new_var_name
                    new_var=irgrip.slurp_any_code(f"{new_var_type}, POINTER :: {new_var_name}")
                    routine.spec.insert(-2, new_var)
                elif (var_routine.type.dtype in ["CPG_OPTS_TYPE"]):
                #elif (var_routine.type.dtype.upper() in ["CPG_OPTS_TYPE"]):
                    #TODO
                    print("Var : ", var_routine, " is of type CPG_OPTS_TYPE.")
                else: #derive_type not field_api and not CPG_OPTS_TYPE                               
                    print("====================================================================")
                    print("Argument = ", arg_name, "not in field api index, neither CPG_OPTS_TYPE!!!")
                    print("====================================================================")
    
            else: 
                if arg.name in dcls:
                    arg_name=arg.name
                    call_arrays[arg_name]="YL_"+arg_name #call_arrays[Z_A]=YL_ZA
                    print(" ************ 3 adding var to call_attays   ****************") 
                    print("arg_name= ",  arg_name)

                if isinstance(arg, Scalar):
                    call_scalar.append(arg_name)
        else: #if call arg is logical or/and
            print("Argument = ", arg_name, "ignored, logical statement")














#def change_dummy_body(routine, lst_dummy_old):
#    """
#    Replace A%B%C by Z_A_B_C in the routine body according to the list lst_dummy_old
#    :param routine:.
#    :param lst_dummy_old: list of var to change
#    """
#    verbose=False
#    variable_map={}          
#    for var in FindVariables().visit(routine.body):
#        if var.name in lst_dummy_old: 
#            new_name="Z_"+var.name.replace("%", "_")
#            if verbose: print("var.name= ", var.name)
#            if verbose: print("new_name= ", new_name)
#
#            variable_map[var]=var.clone(name=new_name)
#    routine.body = SubstituteExpressions(variable_map).visit(routine.body)


def generate_lhook(subname, name, area1, area2, n):
    hookcode="IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:{area1}',{n},ZHOOK_HANDLE_{area2})\n"
    return(hookcode)

def lhook(area, n, handle):
    hookcode=f"IF (LHOOK) CALL DR_HOOK ('{area}',{n},ZHOOK_HANDLE_{handle})\n"
    return(hookcode)
def generate_get_data(call_arrays, machine, area):
    """
    machine : HOST or  DEVICE
    call_arrays : var of the call of the region.  #lhs => get_data(rhs) : call_arrays[lhs]=rhs
    intent[lhs] : RDWR or RDONLY for lhs
    area: GET_DATA or SYNCHOST
    """

    str_get_data=""
    #codetarget=f"IF (LPARALLELMETHOD ('{target}','{subname}:{name}')) THEN\n" #"{target}_SECTION" is replaced by code 
    #str_get_data=str_get_data+codetarget
    strhook=f"{subname}:{name}:{area}"
    hookcode=lhook(strhook, "0", "FIELD_API")
    str_get_data=str_get_data+hookcode
    for var in call_arrays: #lhs => get_data(rhs) : call_arrays[lhs]=rhs
        lhs=var
        print("call_arrays[lhs]  = ",  call_arrays[lhs])
        #============================================================
        #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({call_arrays[lhs]})\n"
        #          TODO INTENT => get interface and check intent of var
        #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({call_arrays[lhs]})\n"
        #============================================================
        datacode=f"{lhs} => GET_{machine}_DATA_RDWR ({call_arrays[lhs]})\n"
        str_get_data=str_get_data+datacode
    hookcode=lhook(strhook, "1", "FIELD_API")
    str_get_data=str_get_data+hookcode
    return(str_get_data)

def generate_null(call_arrays, subname, name):
    str_nullify=""
    area="NULLIFY"
    strhook=f"{subname}:{name}:{area}"
    hookcode=lhook(strhook,"0", "FIELD_API")
    str_nullify=str_nullify+hookcode
    for var in call_arrays: #lhs => get_data(rhs) : call_arrays[lhs]=rhs
       lhs=var
       nullcode=f"{lhs} => NULL ()\n"
       str_nullify=str_nullify+nullcode
    hookcode=lhook(strhook, "1", "FIELD_API")
    str_nullify=str_nullify+hookcode
    return(str_nullify)

source = Sourcefile.from_file(sys.argv[1])

#*********************************************************
#             Creating lst of dim for derive types
#*********************************************************


#print(map_field)
#f=open("map_field.txt", "x")
#f.write(map_field)

#with open('map_field.txt', 'w') as 

#*********************************************************
#*********************************************************

import sys
path_irgrip="/home/cossevine/kilo/src/kilo"
sys.path.append(path_irgrip)
import irgrip

import logical_lst
import logical
import pickle

lst_horizontal_size=["KLON","YDCPG_OPTS%KLON","YDGEOMETRY%YRDIM%NPROMA","KPROMA", "YDDIM%NPROMA", "NPROMA"]
true_symbols, false_symbols = logical_lst.symbols()
false_symbols.append('LHOOK')

with open('field_index.pkl', 'rb') as fp:
    field_index= pickle.load(fp)
map_dim={} #map_dim[old_field]=new_field(:,:,;...)
lst_derive_type=[] #store derive types that are added to the routine spec
for routine in source.routines:
   
    map_dim={}
    logical.transform_subroutine(routine, true_symbols, false_symbols)
    resolve_associates(routine)

    dcls=get_dcls(routine, lst_horizontal_size)
    change_arrays(routine, dcls, lst_horizontal_size, map_dim)
    #dcls=[ decl for decl in FindNodes(VariableDeclaration).visit(routine.spec)]
    need_field_api = set()
    new_routine_name = routine.name + "_PARALLEL"
    regions=GetPragmaRegionInRoutine(routine)
    PragmaRegions=FindNodes(PragmaRegion).visit(routine.body)
    for i in range(len(regions)):
        print(regions[i])
        print(i)
        region=regions[i]
        Pragma=PragmaRegions[i]
        print("region", routine.name)
        calls=[call for call in FindNodes(CallStatement).visit(region["region"])]
        name=region['name']
        subname=routine.name
        new_args = dict()

        call_arrays={}
        call_scalar=[]
   
    
     
       # if target=='OPENMP':
    	##CALL BUILD ARG LST
     	
        for call in calls:
            compute_call(routine, call, field_index, call_arrays, call_scalar, lst_derive_type, map_dim, lst_horizontal_size)
#            args_callee = get_callee_args_of(call.name)
        if len(calls) >1:
            print(" ************************ CAUTION MORE THAN ONE CALL IN A REGION  *****************")
        code_target=""
        for target in region['targets']:
           print("target = ", target)
           if target=='OpenMP':
               print("*****OpenMPEN MP ******")
               str_openmp=generate_openmp(routine, calls, map_dim, call_arrays)
               node_openmp=irgrip.slurp_any_code(str_openmp)
               print("call_arrays = ",  call_arrays)
               print(str_openmp)
       #        print(fgen(node_openmp))
       #        file11=open("nodemp.txt", "w")
       #        file11.write(str_openmp)
       #        file11.close()
        #       exit(1)

       # else if target=='OPENMPSINGLECOLUMN':
       # else if target=='OPENACCSINGLECOLUMN':
       # else:
       #     print(colored("This target isn't defined!"))

#            local_vars = get_local_varnames(routine)
#            for v in call.arguments:
#                if v.name in local_vars:
#                    need_field_api.add(v.name)
#
#            if len(call.arguments) != len(args_callee):
#                print("Error differents lengths", len(call.arguments), len(args_callee))
#                sys.exit(-1)
#
#            omp_target = gen_omp_target(
#                new_routine_name, call.name, call.arguments, args_callee, need_field_api
#            )
#
#            vmap = {}
#            for arg in call.arguments:
#                try:
#                    vmap[arg] = Variable(name=new_args[arg.name]["name"])
#                except:
#                    vmap[arg] = arg
#            call = SubstituteExpressions(vmap).visit(call)
#
#            regAddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, field_new_lst, dcls)["region"].prepend(call)
#            reg["region"].prepend(Comment(text=omp_target))
#
#        ifguard = f"IF (LHOOK) CALL DR_HOOK ('{new_routine_name}:{reg['name']}',0,ZHOOK_HANDLE_PARALLEL)"
#        reg["region"].prepend(Comment(text=ifguard))
#        ifguard = ifguard.replace(",0,", ",1,")
#        reg["region"].append(Comment(text=ifguard))
#
#    ptf = PointerToField(need_field_api)
#    ptf.apply(routine)

        #change_dummy_body(routine, lst_dummy_old)
Sourcefile.to_file(source.to_fortran(), Path("src/out.F90"))

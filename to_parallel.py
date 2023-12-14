import sys
from loki import *
from pathlib import Path
import re

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

def change_arrays(routine, dcls, lst_horizontal_size, dict_dim_array, region_vars, region_vars):
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
        dict_dim_array[var.name]=dd
        region_vars[var.name]="YL_"+var_routine.name
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


#def GetPragmaRegionInSources(sources):
#	# InsertPragmaRegionInSources(sources)
#    routines = sources.routines
#    pragma_regions = []
#    for routine in routines:
#	    pragma_regions.extend(GetPragmaRegionInRoutine(routine))
#    return pragma_regions


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


#class PointerToField(Transformation):
#	# Given a routine and a list of variables names, each variable of the
#    # routine present in the list will be transformed into a pointer of assumed
#    # shape dimension and a corresponding Field API variable will be created
#    def __init__(self, names):
#	    super().__init__()
#	self._names = names
#
#    def transform_subroutine(self, routine, **kwargs):
#	    i = 0
#	for stmt in routine.spec.body:
#		i = i + 1
#	    symbols = []
#	    if not isinstance(stmt, VariableDeclaration):
#		    continue
#	    decl = stmt
#	    for var in decl.symbols:
#		    if var.name in self._names:
#			    t = SymbolAttributes(
#					    dtype=DerivedType(
#						    name="FIELD_" + str(len(var.dimensions) + 1) + "RB"
#						    ),
#					    polymorphic=True,
#					    pointer=True,
#					    )
#			    symbols.append(Scalar(name="YL_" + var.name, type=t))
#	    if symbols:
#		    routine.spec.insert(i - 1, VariableDeclaration(symbols=symbols))
#		i = i + 1
#
#	variables = FindVariables().visit(routine.spec)
#	vmap = {}
#	for v in variables:
#		if v.name in self._names:
#			assumed = tuple(RangeIndex((None, None)) for _ in v.shape)
#		assumed = assumed + (assumed[0],)
#		vmap[v] = v.clone(
#				dimensions=assumed,
#				type=v.type.clone(pointer=True),
#				)
#	else:
#		vmap[v] = v
#
#	routine.spec = SubstituteExpressions(vmap).visit(routine.spec)

#
#def get_local_varnames(routine):
#	# Get variables which are locally declared (not the one given into arguments)
#    local_var = set([v.name for v in routine.variables])
#    upvalues = set([v.name for v in routine.arguments])
#    local_var = local_var - upvalues
#    return list(local_var)
#

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
#
#
#class AddPointerToExistingFieldAPI(Transformation):
#	# Check if the argument is a member of an existing field api object, and if
#    # so create a correspongind local pointer pointing to it
#    def __init__(self, callee, args):
#	    super().__init__()
#	self.callee = callee
#	self.args = args
#	self.args_in_callee = get_args_decl(callee) #Why????

#    def transform_subroutine(self, routine, **kwargs):
#        variables = FindVariables().visit(routine.spec)
#    new_vars = []
#    i = 0
#def AddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, map_dummy, field_new_lst, dcls, lst_dummy_old, dict_dummy_dim):
 











def compute_call(routine, field_index, 
    """
    :param routine:.
    :param field_index: index of field api struct members 
    :param call_arrays: mapping of names. call_arrays[Z_...]=YL_Z...; call_arrays[Z_A_B_C...]=A%B%C
    :param call_scalar
    :param ???
    :param lst_derive_type: lst of derived type that were already added to the routine spec
    :param dcls: maps the derive type name with its declaration in order to insert new dcl node at theright place
    """
    for arg in call.arguments:
        #arg can be logical and/or: "YDCPG_OPTS%YRSURF_DIMS%YSD_VVD%NUMFLDS>=8.AND.YDMODEL%YRML_PHY_MF%YRPHY"
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            arg_name=arg.name
            if '%' in arg_name: # 1) derive_type already on lst_derive_type, 2) derive_type in index, 3) derive_type CPG_OPTS_TYPE 
                arg_basename=arg_name.split("%")[0]
                var_routine=routine.variable_map[arg_basename]
                arg_name_=arg_name_='%'.join(arg_name.split("%")[1:])
                if arg_name in lst_derive_type: #1) derive_type already on lst_derive_type
                    new_name="Z_"+arg_name.replace("%","_")
                    call_arrays[new_name]=arg_name
                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                elif arg_name in var_routine.type.dtype.name+"%"+arg_name_ in field_index: #2) derive_type in index 
                    new_name="Z_"+arg_name.replace("%","_")
                    call_arrays[new_name]=arg_name
                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                    lst_derive_type.append(arg_name)
                    key=v.type.dtype.name+'%'+arg_name_] 
                    new_var_type = field_index[key][0] 
                    d=map_field[key][1][:-1]+",:)"
                    dd=re.match("([A-Z0-9]*)(.*)", d)
                    new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+d  #A%B%C => A%B%C(:,:,:)
                    new_var=irgrip.slurp_any_code(f"{new_var_type}, POINTER :: {new_var_name}")
                    routine.spec.insert(-2, new_var)
                elif (var_routine.type.dtype.upper() in ["CPG_OPTS_TYPE"]):
                    #TODO
                else: #derive_type not field_api and not CPG_OPTS_TYPE                               
                    print("====================================================================")
                    print("Argument = ", arg_name, "not in field api index, neither CPG_OPTS_TYPE!!!")
                    print("====================================================================")

            else: #if call arg is a scalar, shouldn't be an array
        else: #if call arg is logical or/and
       














#        #def AddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, map_var, dcls):
#    """
#    :param routine:.
#    :param call: call statement on which args are changed 
#    :param map_field: {leftmost.type%A%B%C : type, kind and size of C}
#    #???!!! FIELD_NEW where???!!!
#    :param lst_local: lst names of local vars of the caller that were already changed
#    :param lst_dummy: lst of dummy args of the caller that were already changed
#    :param map_dummy: dummy_new_name : dummy_new_var
# ###   :param map_var: 
#    :param dcls: var : {var.name : var.declaration}, in order to find the node where var is delcared
#    :param field_new_lst: nodes of FIELD_NEW...
#    :param lst_dummy_old: lst of var name that were already added to caller spec 
#    """
    verbose=True
    #verbose=False
    print("call.name=", call.name)
    """
    arg
    v left most derive type of arg or arg


    """
    lst_scalar=[]
    for arg in call.arguments:
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):

            arg_name=arg.name
            arg_name_old=arg.name
            if (arg_name not in lst_dummy_old): #don't create new var if already exist 
                arg_basename = arg_name.split("%")[0]
                for v in routine.variables:
                    if arg_basename == v.name: #if left most type (or directly var if no derived type) is in routine variables, useless? Direclty catch the routine var through routine_map???
                           #if left most type is field api 
                        if '%' in arg_name:
                            arg_name_='%'.join(arg_name.split("%")[1:])
                            #*************************************************************
                            #*************************************************************
                            #           look in index table
                            #      field is in field api
                            if v.type.dtype.name+'%'+arg_name_ in map_field:
                                #*************************************************************
                                #*************************************************************
                                print("arg_name= ", arg_name)  
                                print("arg_basename= ", arg_basename)  
                                if arg_basename not in routine.variables:
                                    continue
                                    print("arg_basename= ", arg_basename, "not in routine.variables")
        
        #*******        ****************************************************
                                #1) DUMMY ARGS of the caller
             	        	    #Dummy args YD_A%B => Z_YD_A_B
                                #build a dict of new fields and add them to the routine spec after analysing all the calls
                                #if contains_field_api_member(v.type.dtype.name):
                                if not contains_ignore(v.type.dtype.name): # ===> REMOVE????!!!!!
        #*******        ****************************************************
        
                                    if verbose: print("Dummy arg:", arg_name)
                                    name = "Z_" + arg_name.replace("%", "_") #Z_YD_...
                                    region_vars[name]=arg_name
              #### SHOULD BE USELESS NOW                      if name not in routine.variables and name not in map_dummy: #if var was already added to list of dummy var to changed or already in routine variables
        #A%B%C i        s type(A)%B%C in map_field dict
                                    new_var_type = map_field[v.type.dtype.name+'%'+arg_name_][0] # STRUCT%A%B => STRUCT_TYPE%A%B
                                    #new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+map_field[v.type.dtype.name+'%'+arg_name_][1][:-1]+",:)"   #A%B%C => A%B%C(:,:,:)
                                    d=map_field[v.type.dtype.name+'%'+arg_name_][1][:-1]+",:)"
                                    dd=re.match("([A-Z0-9]*)(.*)", d)
                                    dict_dummy_dim[arg_name_old]=dd
                                    new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+d  #A%B%C => A%B%C(:,:,:)
                                    print("new_var_name= ", new_var_name) 
                                    print("new_var_type= ", new_var_type) 
                                    new_var=irgrip.slurp_any_code(f"{new_var_type}, POINTER :: {new_var_name}")
                                    print("new_var= ", new_var) 
                                    lst_dummy.append(new_var) #add all of them at the end, to have them next to each other
                                    map_dummy[new_var_name]=new_var
                                    lst_dummy_old.append(arg_name_old)
                                    routine.spec.insert(-2, new_var)
                                #*************************************************************
                                #*************************************************************
                                #           look in index table
                            #     var isn't in field api 
                            else:   
                            #*************************************************************
                            #*************************************************************
                                print("=======================================================")
                                print("Argument = ", arg_name, "not in field api index!!!")
                                print("=======================================================")
            elif (isinstance(v, symbols.Scalar)):
                lst_scalar.append(v)
def change_dummy_body(routine, lst_dummy_old):
    """
    Replace A%B%C by Z_A_B_C in the routine body according to the list lst_dummy_old
    :param routine:.
    :param lst_dummy_old: list of var to change
    """
    verbose=False
    variable_map={}          
    for var in FindVariables().visit(routine.body):
        if var.name in lst_dummy_old: 
            new_name="Z_"+var.name.replace("%", "_")
            if verbose: print("var.name= ", var.name)
            if verbose: print("new_name= ", new_name)

            variable_map[var]=var.clone(name=new_name)
    routine.body = SubstituteExpressions(variable_map).visit(routine.body)


def generate_get_data():
    """
    machine : HOST or  DEVICE
    region_vars : var of the call of the region.  #lhs => get_data(rhs) : region_vars[lhs]=rhs
    intent[lhs] : RDWR or RDONLY for lhs
    """
    lst_get_data=()
    codetarget=f"IF (LPARALLELMETHOD ('{target}','{subname}:{name}')) THEN PRINT *'{target}_SECTION'" #"{target}_SECTION" is replaced by code 
    new_node=irgrip.slurp_any_code(codetarget)
    lst_get_data=lst_get_data+new_code
    newcode="IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:GET_DATA',0,ZHOOK_HANDLE_FIELD_API)"
    newnode=irgrip/slurp_any_code(newcode)
    lst_get_data=lst_get_data+newnode
    for var in call.args:
        if var is in
    for var in region_vars: #lhs => get_data(rhs) : region_vars[lhs]=rhs
        lhs=var
        newcode="{lhs} => GET_{machine}_DATA_{intent[lhs]} ({region_vars[lhs]})"
        newnode=irgrip.slurp_any_code(newcode)
        lst_get_data=lst_get_data+newnode
      
    newcode="IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:GET_DATA',0,ZHOOK_HANDLE_FIELD_API)"
    newnode=irgrip.slurp_any_code(newcode)
    lst_get_date=lst_get_data+newnode

def find_new_arg_names(new_args, call, routine):
    """
    Fills in a dict with : the new arg names if the left most var (A%B%C : A = "left most") is field api
                           the old arg name + need_fa else
    """
    variables = FindVariables().visit(routine.spec)
    for arg in call.arguments:
        if arg.name in ignore_list:
            continue
        arg_basename = arg.name.split("%")[0]

    for v in routine.variables:
           if arg_basename == v.name: #the left most type must be present in the routine args
               if contains_field_api_member(v.type.dtype.name):
                   name = "Z_" + arg.name.replace("%", "_") #Z_YD_...
                   new_args[arg.name] = {"name": name, "need_fa": False}
               else:
                   new_args[arg.name] = {"name": arg.name, "need_fa": True}


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
    map_field= pickle.load(fp)
lst_dummy=[]
lst_local=[]
field_new_lst=() 
map_dummy={}
dict_dim_array={}
dict_dummy_dim={}
lst_dummy_old=[]
region_vars={}
for routine in source.routines:
    logical.transform_subroutine(routine, true_symbols, false_symbols)
    resolve_associates(routine)

    dcls=get_dcls(routine, lst_horizontal_size)
    change_arrays(routine, dcls, lst_horizontal_size, dict_dim_array, region_vars)
    #dcls=[ decl for decl in FindNodes(VariableDeclaration).visit(routine.spec)]
    need_field_api = set()
    new_routine_name = routine.name + "_PARALLEL"
    exit(1)
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
        code=code=f"IF (LHOOK) CALL DR_HOOK ('{subname}:{name}',0,ZHOOK_HANDLE_PARALLEL)"
        new_node=irgrip.slurp_any_code(code)
        new_routine=routine.clone()
        new_routine.body=irgrip.insert_at_node(Pragma, new_node, rootnode=routine.body)
        #new_node=irgrip.insert_at_node(Pragma, node, rootnode=routine.body)
        old_node=new_node
        #new_node=old_node
        #new_node=irgrip.insert_at_node(PragmaRegions[i], 
        new_args = dict()

        for target in region['targets']:
            new_section_target=()
            codetarget=f"IF (LPARALLELMETHOD ('{target}','{subname}:{name}')) THEN PRINT *'{target}_SECTION'" #"{target}_SECTION" is replaced by code 
            new_node=irgrip.slurp_any_code(codetarget)
            new_section=new_section+codetarget
            new_routine.body=irgrip.insert_after_node(old_node, new_node, rootnode=new_routine.body)
            old_node=new_node
    
    
     
       # if target=='OPENMP':
       # else if target=='OPENMPSINGLECOLUMN':
       # else if target=='OPENACCSINGLECOLUMN':
       # else:
       #     print(colored("This target isn't defined!"))
    	##CALL BUILD ARG LST
     	
        #find_new_arg_names(new_args, call, routine) #change struct%A%B in struct_A_B
        # if not call.arguments:
        #     print(f"Subroutine {call.name} has no arguments")
        #     continue
       # AddPointerToExistingFieldAPI(call.name, call.arguments)
        for call in calls:
            AddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, map_dummy, field_new_lst, dcls, lst_dummy_old, dict_dummy_dim, region_vars)
    
#            args_callee = get_callee_args_of(call.name)
#
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

        change_dummy_body(routine, lst_dummy_old)
Sourcefile.to_file(source.to_fortran(), Path("src/out.F90"))

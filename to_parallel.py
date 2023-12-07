import sys
from loki import *
from pathlib import Path
import re

def get_dcls(routine):
    """
    
    """
    dcls={}
    variable_map=routine.variable_map
    decls_map={}
    for decl in FindNodes(VariableDeclaration).visit(routine.spec):
        n=0
        new_decls=()
        for s in decl.symbols:
            new_decl=decl.clone(symbols=(s,))
            new_decls=new_decls+(new_decl,)
            #new_decls.append(decls.clone(symbols=(s,)))
            if isinstance(s, symbols.Array):
                dcls[s.name]=new_decl #map to find var decl when changing it
              #  n=n+1
              #  #new_decls.append(decls.clone(symbols=(s,)))
              #  if n>1:
              #      new_decls.append(decls.clone(symbols=(s,)))
                    
    #    if n>1:
    #        decls_map[decls]=new_decls
        decls_map[decl]=new_decls
    routine.spec=Transformer(decls_map).visit(routine.spec)
#    dcls[s.name]=decls
    return(dcls) #dcls map : var.name : var.declaration 
    

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
def AddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, map_var, dcls):
    for arg in call.args:
        arg_name = str(arg)
        arg_basename = arg_name.split("%")[0]
        if arg_basename not in routine.variables:
            continue
        for v in routine.variables:
            if arg_basename == v:
               #if left most type is field api 
                if contains_field_api_member(v.type.dtype.name):
#***********************************************************
		    #Dummy args YD_A%B => Z_YD_A_B
#***********************************************************
                    name = "Z_" + arg_name.replace("%", "_") #Z_YD_...
        	        #if name not in routine.variables:
                    if name not in routine.variables and name not in new_vars_inout[name]:
                    #if name not in routine.variables and not in new_vars_inout[name]:
#                            lst_dummy.append(new_var)
#A%B%C is type(A)%B%C in map_field dict
                        var_type = map_field[v.type.dtype.name+arg_name.split("%")[1:]][0] 
                        var_name= arg_name.split("%")[:-1]+map_field[v.type.dtype.name+arg_name.split("%")[1:]][1]
                        symbols = []
                            #symbols.append(Array(name=name, dimensions=d, type=t))
        	            #lst_dummy.append(VariableDeclaration(symbols=symbols)) #Z_YD_... variables
                        new_var=irgrip.slurp_any_node(" {var_type}, POINTER :: {var_name}")
                        lst_dummy.append(new_var) #add all of them at the end, to have them next to each other

                else: 
#***********************************************************
                    #local var Z => PT, Z
#***********************************************************
                    if var.name not in lst_local: #the variable may have already been added to the list from a previous call
                        var_routine=routine.variable_map[v]
                        var_routine_dcl=dcls[var_routine.name]
                        #var_routine_dcl=dcls[var_routine.name]
                        lst_local.append(var.name) 
                        d = len(var.dimensions)+1 #FIELD_{d}RB
                        dd = d*":,"
                        dd = dd[:-1]
#                        new_var=slurp_any_code(
#                        new_var=irgrip.insert_at_node(var_routine, new_var, routine.spec)    ## var_routine but var dcl


                        str_node1=f"CLASS (FIELD_{d}RB), POINTER :: YL_{var_routine.name}"
                        new_var1=irgrip.slurp_any_code(str_node1)
                        routine.spec=irgrip.insert_at_node(var_routine_dcl, new_var1, rootnode=routine.spec)
                        #routine.spec=irgrip.insert_at_node(var_routine, new_var1, rootnode=routine.spec)
                        if var_routine.type.kind:
                            
                            str_node2=f"{var_routine.type.dtype.name} (KIND={var_routine.type.kind.name}), POINTER :: {var_routine.name} ({dd})"
                       # var_routine.type.dtype.name     var.type.kind.name
                        else:
                            str_node2=f"{var_routine.type.dtype.name}, POINTER :: {var_routine.name} ({dd})"
                        new_var2=irgrip.slurp_any_code(str_node2)
                        routine.spec=irgrip.insert_after_node(new_var1, new_var2, rootnode=routine.spec)
                        ubound="["
                        lbound="["
                        zero=True #if true, means that lbound=only zero
                        for dim in var_routine.dimensions:
                            #var_routine
                            if type(dim)==expression.symbols.DeferredTypeSymbol:
                                ubound=ubound+dim.name+", "
                                lbound=lbound+"0, "
                            elif type(dim)==expression.symbols.RangeIndex:
#                                if type(dim.children[0])==expression.symbols.Sum:
#                                    lbound=lbound+dim.children[0].children[0].name+
                                ubound=ubound+dim.children[1].name+", "
                                if dim.children[0].value!=0:
                                    zero=False
                                lbound=lbound+str(dim.children[0].value)+", "

                        ubound=ubound[:-1]+']' #rm last coma
                        lbound=lbound[:-1]+']' #rm last coma
                        if zeros:
                            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubounds}, PERSISTENT=.TRUE.)"
                        else:
                            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubounds}, LBOUNDS={lbounds}, PERSISTENT=.TRUE.)"
                        field_node=irgrip.slurp_any_code(field_str)
                        field_lst.append(field_node)


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

map_field={} #dict associating A%B%C with C type and dim. 

def get_lst_derived_type(map_field):
    with open('field.txt', 'r') as field_:
        fields_=field_.readlines()
    for line in fields_:
        field=re.match("(\s*)\'([A-Z0-9_%]+)\'.+\'(.+)\'", line)
        regex="([A-Z]+\s*\(KIND\=[A-Z]+\))(\s:+\s)([A-Z]+.+)"
        #field.group(1)='          '
        #field.group(2)='FIELD_VARIABLES%CSPNL%DM'
        #field.group(3)='REAL(KIND=JPRB) :: DM(:,:)'
        if field:
#            print("field match")
#            print("field=",field)
#            print("fg3=",field.group(3))
            match1=re.match(regex,field.group(3)).group(1)
            match2=re.match(regex, field.group(3)).group(3)
            #match1=REAL(KIND=JPRB)
            #match2=DM(:,:)
            map_field[field.group(2)]=[match1, match2]
            #map_field[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #fields[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #field['SURFACE_VARIABLES%GSD_VD%VCAPE%T1']=['REAL(KIND=JPRB)',T1(:)]
get_lst_derived_type(map_field)
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


lst_dummy=[]
lst_local=[]
map_var={}
for routine in source.routines:
    resolve_associates(routine)
    dcls=get_dcls(routine)
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
            codetarget=f"IF (LPARALLELMETHOD ('{target}','{subname}:{name}')) THEN PRINT *'{target}_SECTION'" #"{target}_SECTION" is replaced by code 
            new_node=irgrip.slurp_any_code(codetarget)
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
            AddPointerToExistingFieldAPI(routine, call, map_field, lst_local, lst_dummy, map_var, dcls)
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
#            reg["region"].prepend(call)
#            reg["region"].prepend(Comment(text=omp_target))
#
#        ifguard = f"IF (LHOOK) CALL DR_HOOK ('{new_routine_name}:{reg['name']}',0,ZHOOK_HANDLE_PARALLEL)"
#        reg["region"].prepend(Comment(text=ifguard))
#        ifguard = ifguard.replace(",0,", ",1,")
#        reg["region"].append(Comment(text=ifguard))
#
#    ptf = PointerToField(need_field_api)
#    ptf.apply(routine)


Sourcefile.to_file(source.to_fortran(), Path("src/out.F90"))

import sys
from loki import *
from pathlib import Path
import re
import json
import copy



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
    l=len(string)
    e=(size-l)//2
    r=(size-l)%2
    if t=="star":
        tt="*"
    print(tt*size)
    print(tt*edge + " "*(e-edge) + string + " "*(e-edge+r) + tt*edge)
    print(tt*size)



def rm_jlon(region):
    loops=[loop for loop in FindNodes(ir.Loop).visit(region)]
    loops_jlon=[loop for loop in loops if loop.variable=="JLON"]
    
    loop_map={}
    
    for loop in loops_jlon:
        loop_map[loop]=loop.body
    
    region=Transformer(loop_map).visit(region)
    return(region)

def add_lines(string, to_add):
    """ In string: to_add before and after each line where the regex matches. 
        to_add = [before, after]
    """
    regex="CALL\s[a-zA-Z0-9_]*\([a-zA-Z0-9_%&\s:,\(\)]*\)"
    before=to_add[0]
    after=to_add[1]
    match=re.search(regex, string, flags=re.MULTILINE)
    if match:
        
        new_call=before+'\n'+match.group(0)+'\n'+after
        new_string=re.sub(regex, new_call, string)
        return(new_string)    
    else:
        return(string)
def get_dcls(routine, lst_horizontal_size):
    """
    1) Clean var declarations : only one per line
    2) Stores NPROMA arrays in a dic : dcls
    :param routine:. 
    :param lst_horizontal_size: lst of possible horizontal size names.
    """

    verbose=False
#    verbose=True

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
    return(dcls) #dcls map : var.name : var.declaration 

def change_arrays(routine, dcls, lst_horizontal_size, map_dim):
#change NPROMA arrays : works only if NPROMA arrays are local var of the routine.
    """
    Changes NPROMA arrays into field api objects : change dcls and add new dcls, field creation and field deletion. Runs once on the whole subroutine at the begining.
    :param dcls: dict of NRPOMA arrays declarations to change.
    :param lst_horizontal_size: lst of possible horizontal size names.
    :param map_dim: map_dim[0] : old_var : new_var+dim 
		    map_dim[1] : old_var : new_var+dim if derive_type; old_va+dim elif array
    """
#******************************************************************
#******************************************************************
                        #LOCAL VARS of the caller, stored in dcls
                        #local var Z => PT Z,YL_Z
                        #build an array with the name of the arrays that were changed, replace the arrays gradually
                        #field_new_lst : creation of the field api objects
			#dfield_new_lst : deletion of the field api objects
#******************************************************************
#******************************************************************
    global map_variables
    verbose=False
    #verbose=True
    str_field_new="IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',0,ZHOOK_HANDLE_FIELD_API)\n"
    str_dfield_new="IF (LHOOK) CALL DR_HOOK ('DELETE_TEMPORARIES',0,ZHOOK_HANDLE_FIELD_API)\n"

    str_spec="" #string containing the new PT dcls associated to the NPROMA loc vars

#==========================================================    
#Loop over the NPROMA loc vars (dlcs)
#==========================================================    
    for dcl in dcls:
        var_dcl=dcls[dcl]
        var=var_dcl.symbols[0]
        var_routine=var
        d = len(var.dimensions)+1 #FIELD_{d}RB
        dd = d*":,"
        dd = dd[:-1]
        map_dim[0][var.name]="YL_"+var_routine.name+"("+dd+")"
        map_dim[1][var.name]=var_routine.name+"("+dd+")"

        map_variables["array"][var.name]={}
        map_variables["array"][var.name]["derived"]="YL_"+var_routine.name
        map_variables["array"][var.name]["array"]=var.name
        map_variables["array"][var.name]["array_dim"]=var.name+"("+dd+")"

        str_node1=f"CLASS (FIELD_{d}RB), POINTER :: YL_{var_routine.name}"
        if var_routine.type.kind:
                                   
            str_node2=f"{var_routine.type.dtype.name} (KIND={var_routine.type.kind.name}), POINTER :: {var_routine.name} ({dd})"
        else:
            str_node2=f"{var_routine.type.dtype.name}, POINTER :: {var_routine.name} ({dd})"
        str_spec=str_spec+str_node1+"\n"+str_node2+"\n"
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
                lbound=lbound+"0, "
 
        ubound=ubound[:-2]+']' #rm last coma and space
        lbound=lbound[:-2]+']' #rm last coma and space
        if not is_lbound:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, PERSISTENT=.TRUE.)"
        else:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, LBOUNDS={lbound}, PERSISTENT=.TRUE.)"
        dfield_str=f"IF (ASSOCIATED (YL_{var_routine.name})) CALL FIELD_DELETE (YL_{var_routine.name})"
        if verbose: print("field_str= ", field_str) 
        str_field_new=str_field_new+"\n"+field_str
        str_dfield_new=str_dfield_new+"\n"+dfield_str

#==========================================================    
#Insert new NPROMA local vars
#==========================================================    
    node_spec=irgrip.slurp_any_code(str_spec)
    routine.spec.insert(-1,node_spec)

#==========================================================    
#Insert field generation associated to the NPROMA loc vars 
#==========================================================    
    new_str="IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',1,ZHOOK_HANDLE_FIELD_API)"
    str_field_new=str_field_new+"\n"+new_str
    field_new=irgrip.slurp_any_code(str_field_new)
    routine.body.insert(2, field_new) #insert at 1 => after first LHOOK 

#==========================================================    
#Insert field deletion associated to the NPROMA loc vars 
#==========================================================    
    new_str="IF (LHOOK) CALL DR_HOOK ('DELETE_TEMPORARIES',1,ZHOOK_HANDLE_FIELD_API)"
    str_dfield_new=str_dfield_new+"\n"+new_str
    dfield_new=irgrip.slurp_any_code(str_dfield_new)
    routine.body.insert(-1, dfield_new) #insert at -1 => after last LHOOK 

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

def generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type, map_region_intent):
    """
    Generates the whole parallel region from IF LPARALLELMETHOD up to ENDIF
    :param region: parallel region that is beging computed
    :param calls: calls of the parallel region : calls=FindNodes(CallStatement).visit(region)
    :param map_dim: map_dim[0] : old_var : new_var+dim 
		    map_dim[1] : old_var : new_var+dim if derive_type; old_va+dim elif array

    :param region_arrays: ??? TODO
    :param parallelmethod: OPENMP, OPENMPSINGLECOLUMN, OPENACCSINGLECOLUMN
    :param subname: subroutine name #remove??
    :param name: region name
    :param args: variables of the region. FindVariables(unique=True).visit(region). A loop is done through args to change their names and idx
    :param region_scalar: list of scalars used in the region. For PRIVATE clauses.
    :param lst_derive_type: lst of derived type that were already added to the routine spec. When looping through the region var, when a derive type is detected the array associated to it won't be added again to the routine spec.
    """

    str_compute=()
#==========================================================    
#Generate GET_DATA region
#==========================================================    
    str_compute=f"IF (LPARALLELMETHOD ('{parallelmethod}','{subname}:{name}')) THEN\n"
    if parallelmethod=="OPENACCSINGLECOLUMN":
        str_data=generate_get_data(region_arrays, "DEVICE", "GET_DATA", subname, name, map_region_intent)
    else:
        str_data=generate_get_data(region_arrays, "HOST", "GET_DATA", subname, name, map_region_intent)
    str_compute=str_compute+str_data
#==========================================================    
#Generate COMPUTE region
#==========================================================    
    strhook=f"{subname}:{name}:COMPUTE"
    hookcode=lhook(strhook,"0", "COMPUTE")
    str_compute=str_compute+hookcode
    if parallelmethod=="OPENMP":
        str_compute=str_compute+generate_compute_openmp(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type)
    elif parallelmethod=="OPENMPSINGLECOLUMN" or "OPENACCSINGLECOLUMN":
        str_compute=str_compute+generate_compute_scc(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type, parallelmethod)
	    
	    #str_compute=str_compute+generate_compute_openmpscc(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type, parallelmethod):
   # elif parallelmethod=="OPENACCSINGLECOLUMN":
   #     str_compute=str_compute+generate_compute_openaccscc(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type)
#


    hookcode=lhook(strhook,"1", "COMPUTE")
    str_compute=str_compute+hookcode 
#==========================================================    
#Generate LSYNCHOST region
#==========================================================    
    strifsync=f"IF (LSYNCHOST ('{subname}:{name}')) THEN\n"
    str_compute=str_compute+strifsync
    strsynchost=generate_get_data(region_arrays, "HOST", "SYNCHOST", subname, name, map_region_intent)
    str_compute=str_compute+strsynchost
    strifsync="ENDIF\n"
    str_compute=str_compute+strifsync
#==========================================================    
#Generate NULLIFY region
#==========================================================    
    str_null=generate_null(region_arrays, subname, name)
    str_compute=str_compute+str_null
    str_compute=str_compute+"ENDIF\n"   #=> ENDIF must be removed by next compute area of the current region.  
    return(str_compute)  

def generate_variables(args, str_body_, map_dim):
    """
    Change variables of the region : add JBLK and change var name.
    :param map_dim: map_dim[0] : old_var : new_var+dim 
		    map_dim[1] : old_var : new_var+dim if derive_type; old_var+dim elif array

    """ 
    global map_variables
    #verbose=True
    verbose=False

###    def find_arg_old(string, arg_name, regex):
####        match=re.search(regex, string, flags=re.MULTILINE)
###        """
###        regex="(\\b"+fgen(arg.name)+"\\b)(\s*\([^)]*\))*"
###	Return a iterable of all the matches : 
###
###	And for each match, example : 
###	
###	find_arg(name(:,1, JLON)) => group(0) = name(:,1, JLON), group(1) = name, group(2) = (:,1, JLON)
###	find_arg(nametoto) => None; because nametoto isn't name, we only want to match 'name'
###	find_arg(name) => group(0) = name, group(1) = name, group(2) = None
###       
###	"""
###        match=re.finditer(regex, string, flags=re.MULTILINE)
###        return(match)
###    for arg in args: 
###        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
####            if arg.name in map_dim[1]:
###                regex="(\\b"+fgen(arg.name)+"\\b)(\s*\([^)]*\))*"
###                new_arg=map_dim[1][arg.name]
###                new_arg_name=re.match("[a-zA-Z0-9_%]+", new_arg) #can use region_arrays to have directly name without dimensions...
###                iter_match=find_arg(str_body_, arg.name, regex)
###                
###                if not iter_match:
###                    bprint("NO MATCH")
###                else:
###                    for match in reversed(list(iter_match)):
###                        begin, end = match.start(), match.end()
###                        if match.group(2): #if array already has some shapes: keep them and add JBLK at the end.
###                            new_arg_dim=match.group(2)[:-1]+",JBLK)"
###                            new_arg=new_arg_name.group(0)+new_arg_dim
###                            if verbose: print("new_arg=", new_arg)
###                          #  str_body_=re.sub(regex, new_arg, str_body_)
###                            str_body_ = str_body_[:begin]+new_arg+str_body_[end:]
###                        else: #if array has no shape : add them and add JBLK
###                            new_arg=map_dim[1][arg.name].replace(":)","JBLK)")
###                         #   str_body_=re.sub(regex, new_arg, str_body_)
###                            str_body_ = str_body_[:begin]+new_arg+str_body_[end:]
###    return(str_body_+"\n")


    def find_arg(string, arg_name, regex):
#        match=re.search(regex, string, flags=re.MULTILINE)
        """
        regex="(\\b"+fgen(arg.name)+"\\b)(\s*\([^)]*\))*"
	Return a iterable of all the matches : 

	And for each match, example : 
	
	find_arg(name(:,1, JLON)) => group(0) = name(:,1, JLON), group(1) = name, group(2) = (:,1, JLON)
	find_arg(nametoto) => None; because nametoto isn't name, we only want to match 'name'
	find_arg(name) => group(0) = name, group(1) = name, group(2) = None
       
	"""
        match=re.finditer(regex, string, flags=re.MULTILINE)
        return(match)

    for arg in args: 
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            if arg.name in map_variables["array"] :
                key="array"
            elif arg.name in map_variables["derived"] :
                key="derived"
            else:
                key = None 

            if key == "array" or key == "derived": 
#            if arg.name in map_dim[1]:
                regex="(\\b"+fgen(arg.name)+"\\b)(\s*\([^)]*\))*"
               # new_arg=map_dim[1][arg.name]
                new_arg=map_variables[key][arg.name]["array_dim"]
                new_arg_name=re.match("[a-zA-Z0-9_%]+", new_arg) #can use region_arrays to have directly name without dimensions...
                iter_match=find_arg(str_body_, arg.name, regex) #find all the places where the var appears
                
                if not iter_match:
                    bprint("NO MATCH, THE VAR WASN'T FOUND BY THE REGEX")
                else:
                    for match in reversed(list(iter_match)):
                        begin, end = match.start(), match.end()
                        if match.group(2): #if array already has some shapes: keep them and add JBLK at the end.
                            new_arg_dim=match.group(2)[:-1]+",JBLK)"
                            new_arg=new_arg_name.group(0)+new_arg_dim
                            if verbose: print("new_arg=", new_arg)
                          #  str_body_=re.sub(regex, new_arg, str_body_)
                            str_body_ = str_body_[:begin]+new_arg+str_body_[end:]
                        else: #if array has no shape : add them and add JBLK
#                            new_arg=map_dim[1][arg.name].replace(":)","JBLK)")
                            new_arg=map_variables[key][arg.name]["array_dim"].replace(":)","JBLK)")
                         #   str_body_=re.sub(regex, new_arg, str_body_)
                            str_body_ = str_body_[:begin]+new_arg+str_body_[end:]

    return(str_body_+"\n")


def generate_compute_openmp(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type):
   """
   Generates openmp compute code. 
   :param calls: calls of the parallel region : calls=FindNodes(CallStatement).visit(region)
   :param region: parallel region that is beging computed
   :param args: variables of the region. FindVariables(unique=True).visit(region). A loop is done through args to change their names and idx
   :param map_dim: map_dim[0] : old_var : new_var+dim 
                   map_dim[1] : old_var : new_var+dim if derive_type; old_va+dim elif array
   :param region_scalar: list of scalars used in the region. For PRIVATE clauses.
   :param region_arrays: ??? TODO
   :param lst_derive_type: lst of derived type that were already added to the routine spec. When looping through the region var, when a derive type is detected the array associated to it won't be added again to the routine spec.
"""
   str_body=fgen(region.body)
   str_body=generate_variables(args, str_body, map_dim)
   str_openmp=""
   code="CALL YLCPG_BNDS%INIT (YDCPG_OPTS)\n"
   str_openmp=str_openmp+code 
   if region_scalar:
       private="JBLK"
   else:
       private="JBLK"
   firstprivate="YLCPG_BNDS"
   code=f"!$OMP PARALLEL DO PRIVATE ({private}) FIRSTPRIVATE({firstprivate})\n"
   str_openmp=str_openmp+code 
   code="DO JBLK = 1, YDCPG_OPTS%KGPBLKS\n"
   str_openmp=str_openmp+code
   code="CALL YLCPG_BNDS%UPDATE (JBLK)\n"
   str_openmp=str_openmp+code
   str_openmp=str_openmp+str_body #add region body:
   str_openmp=str_openmp+"ENDDO\n"
#   file1=open("myfile.txt", "w")
#   file1.write(json.dumps(map_dim))
#   file1.close()

   return(str_openmp)


def generate_compute_scc(calls, region, args, map_dim, region_scalar, region_arrays, lst_derive_type, parallelmethod):
   """
   Generates openmp single column compute code. 
   1) Creation of the region : add jlon loop around CALL, add _OPENACC and YDSTACK in CALL, change variables, replace JLON loops by (loop + stack_l/stack_u ... + acc if needed)
   2) generate pragma and loops : openmp or openacc
   3) insert 2) in code => at each jlon loops and/or at jblk loop

   :param calls: calls of the parallel region : calls=FindNodes(CallStatement).visit(region)
   :param region: parallel region that is beging computed
   :param args: variables of the region. FindVariables(unique=True).visit(region). A loop is done through args to change their names and idx
   :param map_dim: map_dim[0] : old_var : new_var+dim 
                   map_dim[1] : old_var : new_var+dim if derive_type; old_va+dim elif array
   :param region_scalar: list of scalars used in the region. For PRIVATE clauses.
   :param region_arrays: ??? TODO
   :param lst_derive_type: lst of derived type that were already added to the routine spec. When looping through the region var, when a derive type is detected the array associated to it won't be added again to the routine spec.
   """

#   def change_jl_loop(str_region, acc=None):
#       """
#       Change JLON loops in loops with stack statements.
#       :param str_region: string of the region.
#       :param acc: only for acc code: add ACC declarations before the JLON statement.
#       """
#       if acc:
#           code=acc
#       else:
#           code=""
#      
#      
#       str_jlon="DO JLON = 1, MIN (YDCPG_OPTS%KLON, YDCPG_OPTS%KGPCOMP - (JBLK - 1) * YDCPG_OPTS%KLON)\n"
#       str_jlon=code+str_jlon
#       code="YLCPG_BNDS%KIDIA = JLON\n"
#       str_jlon=str_jlon+code
#       code="YLCPG_BNDS%KFDIA = JLON\n"
#       str_jlon=str_jlon+code
#       code="YLSTACK%L = stack_l (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
#       str_jlon=str_jlon+code
#       code="YLSTACK%U = stack_u (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
#       str_jlon=str_jlon+code
#       regex="DO JLON.*"
#       str_region=re.sub(regex,str_jlon, str_region) #insert in str_region, at line DO JLON =, str_jlon
#       return(str_region)
 
   def generate_pragma_openmpscc(region_scalar):
   
       str_openmpscc=""
       code="CALL YLCPG_BNDS%INIT (YDCPG_OPTS)\n"
       str_openmpscc=str_openmpscc+code 
       if region_scalar:
           private="JBLK, JLON, YLCPG_BNDS, YLSTACK"
           #private="JBLK,"+",".join(region_scalar)
       else:
           private="JBLK, JLON, YLCPG_BNDS, YLSTACK"
       code=f"!$OMP PARALLEL DO PRIVATE ({private})\n"
       str_openmpscc=str_openmpscc+code 
       code="DO JBLK = 1, YDCPG_OPTS%KGPBLKS\n"
       str_openmpscc=str_openmpscc+code
       return(str_openmpscc)

   def generate_pragma_openaccscc(region_arrays, region_scalar):
       str_openaccscc=""
       code="CALL YLCPG_BNDS%INIT (YDCPG_OPTS)\n"
       str_openaccscc=str_openaccscc+code 
       code="!$ACC PARALLEL LOOP GANG &\n"
       str_openaccscc=str_openaccscc+code 
       present="!$ACC&PRESENT("
       count_present=0 #having to long lines, bug with !$acc as comments and lines to long
       for array in region_arrays:
           if count_present==0:
               present=present+array
               count_present=1
           else:
               if count_present%3==0:
                  present=present+", &\n"
                  present=present+"!$ACC&        "
                  present=present+array
                  count_present+=1
               else:
                   present=present+","+array
                   count_present+=1
                 
       present=present+") &\n"
#       code=f"""
#            !$ACC&PRESENT({present}) &\n 
#       """
       str_openaccscc=str_openaccscc+present
       code="!$ACC&PRIVATE (JBLK) &\n"
       str_openaccscc=str_openaccscc+code 
       code="!$ACC&VECTOR_LENGTH (YDCPG_OPTS%KLON)\n"
       str_openaccscc=str_openaccscc+code
       code="DO JBLK = 1, YDCPG_OPTS%KGPBLKS\n"
       str_openaccscc=str_openaccscc+code

       if region_scalar:
           #private="JBLK,"+",".join(region_scalar)
           private="JBLK, JLON, YLCPG_BNDS, YLSTACK"
       else:
           private="JBLK, JLON, YLCPG_BNDS, YLSTACK"
#       code=f"""
#            !$ACC LOOP VECTOR &\n
#            !$ACC&PRIVATE ({private})\n"""
       code=f"!$ACC LOOP VECTOR PRIVATE ({private}) \n"
       str_openaccscc=str_openaccscc+code
       return(str_openaccscc)

   if parallelmethod=="OPENMPSINGLECOLUMN":
       str_jlon=generate_pragma_openmpscc(region_scalar)
   elif parallelmethod=="OPENACCSINGLECOLUMN":
       str_jlon=generate_pragma_openaccscc(region_arrays, region_scalar)

   code="DO JLON = 1, MIN (YDCPG_OPTS%KLON, YDCPG_OPTS%KGPCOMP - (JBLK - 1) * YDCPG_OPTS%KLON)\n"
   str_jlon=str_jlon+code
   code="YLCPG_BNDS%KIDIA = JLON\n"
   str_jlon=str_jlon+code
   code="YLCPG_BNDS%KFDIA = JLON\n"
   str_jlon=str_jlon+code
   code="YLSTACK%L = stack_l (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
   str_jlon=str_jlon+code
   code="YLSTACK%U = stack_u (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
   str_jlon=str_jlon+code

   region=rm_jlon(region)
   str_region=fgen(region.body)
   
   ###str_jlon=["DO JLON=YDCPG_BNDS%KIDIA,YDCPG_BNDS%KFDIA", "ENDDO"]
   ###str_region=add_lines(str_region, str_jlon) #add JLON loops around CALL statements
   str_region=generate_call(calls, str_region) #add _OPENACC and YDSTACK 
   str_region=generate_variables(args, str_region, map_dim) #change variables (YL->Z_YL; +dim + JBLK)
   str_region=str_jlon+str_region #add horizontal loop at the top of the region.


   code="ENDDO\n"
   str_region=str_region+code
   code="ENDDO\n"
   str_region=str_region+code
  
  
   return(str_region)

def generate_call(calls, str_region):
    """
    Changes the calls in calls : add _OPENACC to their name and YDSTACK=YLSTACK to the routine args.
    :param calls: calls of the parallel region : calls=FindNodes(CallStatement).visit(region)
    :param str_region: string of region
    """
    if not calls:
        return(str_region)
    for call in calls:
        str_call=fgen(call)
        regex="CALL\s"+fgen(call.name)
        call_name=re.match(regex, str_call).group(0)
        str_call=str_call.replace(call_name, call_name+"_OPENACC")
        str_call=str_call[:-1]+", YDSTACK=YLSTACK)\n"
        regex="CALL\s"+fgen(call.name)+"\([a-zA-Z0-9_%&\s:,\(\)]*\)"
        str_region=re.sub(regex,str_call, str_region, flags=re.MULTILINE) #insert in str_region, at the place of the call
        return(str_region)
    
ignore_list = [
        "YDCPG_BNDS%KIDIA",
        "YDCPG_BNDS%KFDIA",
        "YDGEOMETRY",
        "YDMODEL",
       ]

def get_args_decl(subname):
    verbose=False
    filename = "src/" + str(subname).lower() + ".F90"
    file = Sourcefile.from_file(filename)
    if verbose: print(type(file.routines[0].arguments[0]))
    if verbose: print(file.routines[0].arguments[0])
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



def compute_region(routine, args, field_index, region_arrays, region_scalar, lst_derive_type, map_dim, lst_horizontal_size, dcls):
    """
    Changes a parallel area : 
    1) v



    :param routine:.
    :param field_index: index of field api struct members 
    :param region_arrays: mapping of names. region_arrays[Z_...]=YL_Z...; region_arrays[Z_A_B_C...]=A%B%C
    :param region_scalar
    :param ???
    :param lst_derive_type: lst of derived type that were already added to the routine spec
#######    :param dcls: maps the derive type name with its declaration in order to insert new dcl node at theright place
    """
##========================================================== 
#region_arrays[Z_...] = derived_type
#region_arrays[lhs] = rhs
#lhs => get_data(rhs)
#
#region_arrays is used to generate get_data code.
##========================================================== 


##==========================================================    
##Init to empty:
#    region_arrays={}
#    region_scalar=[]
##==========================================================    
    global map_variables
    verbose=False
    #verbose=True
#    for arg in call.arguments:
    for arg in args:
        if verbose: print("arg = ",  arg)
        #arg can be logical and/or: "YDCPG_OPTS%YRSURF_DIMS%YSD_VVD%NUMFLDS>=8.AND.YDMODEL%YRML_PHY_MF%YRPHY"
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            arg_name=arg.name

#==========================================================    
#==========================================================    
#I) arg is a derive type:
#==========================================================    
#==========================================================    
            if '%' in arg_name: 
                arg_basename=arg_name.split("%")[0]
                var_routine=routine.variable_map[arg_basename]
                if var_routine.type.dtype.name=="MF_PHYS_SURF_TYPE": #remove P
                    arg_name__="%".join(arg_name.split("%")[:-1])+"%F_"+arg_name.split("%")[-1:][0][1:] #remove extra P
                else:
                    arg_name__="%".join(arg_name.split("%")[:-1])+"%F_"+arg_name.split("%")[-1:][0] #A%B%C => A%B%F_C
                arg_name_=arg_name_='%'.join(arg_name.split("%")[1:])
#==========================================================    
#I-1) derive_type already on lst_derive_type
#==========================================================    
                if arg_name__ in lst_derive_type: 
                    new_name="Z_"+arg_name.replace("%","_")
                    region_arrays[new_name]=[arg_name__, arg.name] #????
                    new_arg=arg.clone(name=new_name)  #useless?
#==========================================================    
#I-2) derive_type not in lst_derive_type but in index
#The array associated to the derive type must be created and added to the routine spec
#==========================================================    
                elif (var_routine.type.dtype.name+"%"+arg_name_ in field_index):  
                #elif arg_name in var_routine.type.dtype.name+"%"+arg_name_ in field_index: #2) derive_type in index 
                    new_name="Z_"+arg_name.replace("%","_")
                    region_arrays[new_name]=[arg_name__, arg.name]
                    new_arg=arg.clone(name=new_name) #useless?
                    lst_derive_type.append(arg_name__)
                    key=var_routine.type.dtype.name+'%'+arg_name_
                    new_var_type = field_index[key][0] 
                    d=field_index[key][1][:-1]+",:)"
                    dd=re.match("([A-Z0-9]*)(.*)", d)
                    new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+d  #A%B%C => A%B%C(:,:,:)
                    map_dim[0][arg_name]=new_var_name
                    map_dim[1][arg_name]=new_var_name

                    map_variables["derived"][arg_name]={}
                    #map_variables["derived"][arg_name]["array"]=new_var_name
                    map_variables["derived"][arg_name]["array_dim"]=new_var_name
                    map_variables["derived"][arg_name]["derived"]=arg_name__
                    
                    new_var=irgrip.slurp_any_code(f"{new_var_type}, POINTER :: {new_var_name}")
                    routine.spec.insert(-1, new_var)
#==========================================================    
#I-3) derive_type not in index
#==========================================================    
                elif (var_routine.type.dtype in ["CPG_OPTS_TYPE"]):
                #elif (var_routine.type.dtype.upper() in ["CPG_OPTS_TYPE"]):
                    #TODO
                    if verbose: 
                        to_print="Var : "+ var_routine+ " is of type CPG_OPTS_TYPE."
                        bprint(to_print)
                else: #derive_type not field_api and not CPG_OPTS_TYPE                               
                    if verbose: 
                        to_print="Argument = "+ arg_name+ "not in field api index+ neither CPG_OPTS_TYPE!!!"
                        bprint(to_print)
#==========================================================    
#==========================================================    
#II) arg isn't a derive type
#==========================================================    
#==========================================================    
   
            else: 

#==========================================================    
#II-1) arg is an array 
#==========================================================    
                if arg.name in dcls:
                    arg_name=arg.name
                    region_arrays[arg_name]=["YL_"+arg_name, arg.name] #region_arrays[Z_A]=YL_ZA
                    if verbose:
                        to_print=f"adding {arg_name} to region_arrays"
                        bprint(to_print)
#==========================================================    
#II-2) arg is a scalar 
#==========================================================    
                if isinstance(arg, Scalar):
                    region_scalar.append(arg_name)
        else: #if call arg is logical or/and
            if verbose: print("Argument = ", arg_name, "ignored, logical statement")


def generate_lhook(subname, name, area0, area2, n):
    hookcode="IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:{area1}',{n},ZHOOK_HANDLE_{area2})\n"
    return(hookcode)

def lhook(area, n, handle):
    hookcode=f"IF (LHOOK) CALL DR_HOOK ('{area}',{n},ZHOOK_HANDLE_{handle})\n"
    return(hookcode)
def generate_get_data(region_arrays, machine, area, subname, name, map_region_intent):
    """
    param: machine : HOST or  DEVICE
    param: region_arrays: var of the call of the region.  #lhs => get_data(rhs) : region_arrays[lhs]=rhs
    param: intent[lhs]:  RDWR or RDONLY for lhs
    param: area: GET_DATA or SYNCHOST
    """
    map_intent_access={}
    map_intent_access['in']="RDONLY"
    map_intent_access['out']="RDWR"
    map_intent_access['inout']="RDWR"

    #verbose=True
    verbose=False
    #intent=False
    intent=True

    str_get_data=""
    strhook=f"{subname}:{name}:{area}"
    hookcode=lhook(strhook, "0", "FIELD_API")
    str_get_data=str_get_data+hookcode
    print("GGmap_region_intent =", map_region_intent)
    for var in region_arrays: #lhs => get_data(rhs) : region_arrays[lhs]=rhs
        lhs=var
        if verbose: print("region_arrays[lhs]  = ",  region_arrays[lhs])
        if intent:
            if region_arrays[lhs][1] in map_region_intent:
                access_type = map_intent_access[map_region_intent[region_arrays[lhs][1]]]
                #access_type = map_intent_access[map_region_intent[lhs]]
            else: #default RDWR
                access_type = "RDWR"

            datacode=f"{lhs} => GET_{machine}_DATA_{access_type} ({region_arrays[lhs][0]})\n"

    #    #============================================================
    #    #TODO : get intent
    #    #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({region_arrays[lhs]})\n"
    #    #          TODO INTENT => get interface and check intent of var
    #    #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({region_arrays[lhs]})\n"
    #    #============================================================
    #    #field=region_arrays[lhs]
    #    #field_="%".join(field.split("%")[:-1])+"%F_"+field.split("%")[-1:] # A%B%C => A%B%F_C
    #    #datacode=f"{lhs} => GET_{machine}_DATA_RDWR ({field_})\n"
        if not intent: #all intent are set to RDWR
            datacode=f"{lhs} => GET_{machine}_DATA_RDWR ({region_arrays[lhs][0]})\n"

        str_get_data=str_get_data+datacode

    hookcode=lhook(strhook, "1", "FIELD_API")
    str_get_data=str_get_data+hookcode
    return(str_get_data)

def generate_null(region_arrays, subname, name):
    str_nullify=""
    area="NULLIFY"
    strhook=f"{subname}:{name}:{area}"
    hookcode=lhook(strhook,"0", "FIELD_API")
    str_nullify=str_nullify+hookcode
    for var in region_arrays: #lhs => get_data(rhs) : region_arrays[lhs]=rhs
       lhs=var
       nullcode=f"{lhs} => NULL ()\n"
       str_nullify=str_nullify+nullcode
    hookcode=lhook(strhook, "1", "FIELD_API")
    str_nullify=str_nullify+hookcode
    return(str_nullify)
#
def add_var(routine):
    """
    Add str_var to the routine where ZHOOK_HANDLE is declared
    """
    stop=False
    for decl in FindNodes(VariableDeclaration).visit(routine.spec):
        for s in decl.symbols:
            if s.name=="ZHOOK_HANDLE":
                str_var="""
                    REAL(KIND=JPHOOK) :: ZHOOK_HANDLE_FIELD_API
                    REAL(KIND=JPHOOK) :: ZHOOK_HANDLE_PARALLEL
                    REAL(KIND=JPHOOK) :: ZHOOK_HANDLE_COMPUTE
                    TYPE(STACK) :: YLSTACK"""
                node=irgrip.slurp_any_code(str_var)
                routine.spec=irgrip.insert_after_node(decl, node, rootnode=routine.spec)
                stop=True
            break
        if stop:
            break

def read_interface(calls,path_interface, map_intent, map_region_intent):
    """    
    map_intent[nom_routine] = [nom : intent]
    """
#    verbose=False
    verbose=True
 #   nb_iter = 0
    debug = True #read interface in /src
    #debug = False #read in real repo
    for call in calls:
#============================================
#!!! Limitation if the names are different from one call to another !!!

# CALL A(B) -> map_intent[A][B] = intent(xxx)
# CALL A(D) -> map_intent[A][D] won't be defined
        if call not in map_intent:
#============================================
            if verbose: print("call =", call.name.name)
            call_name = str(call.name.name.lower())
            call_name = call_name.replace("_openacc","") #_openacc interfaces and regular interfaces are regular interfaces
            map_intent[call_name] = {}
#            call_path = map_path[call_name+'.F90']
            call_path=path_interface+"/"+call_name+".intfb.h"
#            call_path=call_path.replace(".F90",".intfb.h")
            if debug:
                call_path ="/home/gmap/mrpm/cossevine/build_Parallel/"+"src/"+call_name+".intfb.h"
            if verbose: 
                print("call_path =", call_path)
                print("call_name=", call_name)
#            exit(1)
            with open(call_path) as f :
                lines = f.readlines()
            lines = lines[1:-1] #rm INTERFACE and END INTERFACE from the routine...
            content_call = ''.join(lines)
            call_source = Sourcefile.from_source(content_call)
            call_ir = call_source[call_name.upper()]
            if verbose: print("call_ir =", fgen(call_ir))
            for arg_idx in range(len(call_ir.arguments)):
                arg=call.arguments[arg_idx]
                if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
#                    arg_name=call.arguments[arg_idx].name #names in the caller
                    arg_name=arg.name  #names in the caller
                    arg_=call_ir.arguments[arg_idx]
                    map_intent[call_name][arg_name] = arg_.type.intent
#                    if nb_iter == 0:
#                        map_region_intent[arg_name] = map_intent[call_name][arg_name]
#                    else:
                    if arg_name not in map_region_intent:
                        map_region_intent[arg_name]=map_intent[call_name][arg_name]
                    else:
                        map_region_intent[arg_name] = analyse_intent(map_intent[call_name][arg_name], map_region_intent[arg_name]) #comparing intent of the arg in the region with the intent of the arg in the call
 #            nb_iter = nb_iter+1
        print("map_region_intent =",map_region_intent) 
def analyse_intent(intent1, intent2):
    if intent1 or intent2 == 'out':
        return('out')
    elif intent1 or intent2 == 'inout':
        return('inout')
    elif intent1 and intent2 == 'in':
        return('in')
        

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

import sys
path_irgrip="/home/gmap/mrpm/cossevine/kilo/src/acdc/loki"
sys.path.append(path_irgrip)
import irgrip

import logical_lst
import logical
import pickle

import click

@click.command()
#@click.option('--pathr', help='path of the file to open')
#@click.option('--pathw', help='path of the file to write to')
@click.option('--pathpack', help='absolute path to the pack')
@click.option('--pathview', help='path to src/local/... or src/main/...')
@click.option('--pathfile', help='path to the file, with the file name in the path')

@click.option('--horizontal_opt', default=None, help='additionnal possible horizontal idx')
@click.option('--inlined', '-in', default=None, multiple=True, help='names of the routine to inline')


def parallel_trans(pathpack, pathview, pathfile, horizontal_opt, inlined):
    global map_variables

    #----------------------------------------------
    #setup
    #----------------------------------------------
    verbose=True
    #verbose=False
    print("pathpack =", pathpack)
    print("pathview =", pathview)
    print("pathfile =", pathfile)
    
    pathr=pathpack+'/'+pathview+pathfile

    pathw=pathr.replace(".F90", "")+"_parallel"
    
    if verbose: print('pathr=', pathr)
    if verbose: print('pathw=', pathw)
    import logical_lst
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
 
    source=Sourcefile.from_file(pathr) 




    able_mp=True
    #able_mp=False
    able_scc=True
    #able_scc=False
    #able_acc=False
    able_acc=True
    dict_able={}
    dict_parallelmethod={}
    dict_parallelmethod["OpenMP"]="OPENMP"
    dict_parallelmethod["OpenMPSingleColumn"]="OPENMPSINGLECOLUMN"
    dict_parallelmethod["OpenACCSingleColumn"]="OPENACCSINGLECOLUMN"
    dict_able["OpenMP"]=able_mp
    dict_able["OpenMPSingleColumn"]=able_scc
    dict_able["OpenACCSingleColumn"]=able_acc

    lst_horizontal_size=["KLON","YDCPG_OPTS%KLON","YDGEOMETRY%YRDIM%NPROMA","KPROMA", "YDDIM%NPROMA", "NPROMA"]
    true_symbols, false_symbols = logical_lst.symbols()
    #false_symbols.append('LHOOK')

    map_variables = { 
        "array" : {},
        "derived" : {}
    }
#    map_variables["array"] = {}
#    map_variables["derived"] = {}

#==========================================================    
#Loading the index file
#==========================================================    
    with open(pathpack+'/'+'field_index.pkl', 'rb') as fp:
        field_index= pickle.load(fp)
        
#==========================================================    
#Creating the map_path 
#==========================================================    
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

    path_interface=pathpack+'/'+pathview+".intfb/arpifs"
    map_intent={}
    map_dim=[{},{}] #map_dim[old_field]=new_field(:,:,;...)
    lst_derive_type=[] #store derive types that are added to the routine spec
#    for routine in source.routines:
    routine=source.subroutines[0]    

    #----------------------------------------------
    #transformation:
    #----------------------------------------------

    logical.transform_subroutine(routine, true_symbols, false_symbols)
    resolve_associates(routine)

    add_var(routine) #zhook variables
    dcls=get_dcls(routine, lst_horizontal_size) #one dcl per line + return lst of array dcl
    change_arrays(routine, dcls, lst_horizontal_size, map_dim) #creation of field api objetcs associated with each array
    routine_name = routine.name + "_PARALLEL"
#==========================================================    
#Adding modules
#==========================================================    
    str_modules="""
        USE ACPY_MOD
        USE STACK_MOD
        USE YOMPARALLELMETHOD
        USE FIELD_ACCESS_MODULE
        USE FIELD_FACTORY_MODULE
        USE FIELD_MODULE
    """
    code_modules=irgrip.slurp_any_code(str_modules)
    routine.spec.insert(1, code_modules)
    regions=GetPragmaRegionInRoutine(routine)
    PragmaRegions=FindNodes(PragmaRegion).visit(routine.body)

    subname=routine.name

    for i in range(len(regions)):
#==========================================================    
#Init to empty:
        region_arrays={}
        region_scalar=[]
        code_region=""
        map_region_intent={}
#==========================================================    

        region=regions[i]
        Pragma=PragmaRegions[i]
        calls=[call for call in FindNodes(CallStatement).visit(region["region"])]
        
        read_interface(calls,path_interface, map_intent, map_region_intent) #create map_intent[calls]
        #exit(1)
        if verbose: 
            print("Interface map_intent =", map_intent)
            print("Interface map_region_intent =", map_region_intent)
        
        
        name=region['name']
        new_args = dict()
        targets=region["targets"]
        region=region["region"]

        args=FindVariables(unique=True).visit(region)
        
        compute_region(routine, args, field_index, region_arrays, region_scalar, lst_derive_type, map_dim, lst_horizontal_size, dcls)
        print("region_arrays = ", region_arrays)
        if verbose: print("targets = ", targets)
        for target in targets: 
           able=dict_able[target]
           parallelmethod=dict_parallelmethod[target]

           if able:
               str_code=generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type, map_region_intent)
               node_openmp=irgrip.slurp_any_code(str_code)
                #file11=open("nodemp.txt", "w")
                #file11.write(str_openmp)
                #file11.close()
               code_region=code_region+str_code
        node_target=irgrip.slurp_any_code(code_region)
        routine.body=irgrip.insert_at_node(Pragma, node_target, rootnode=routine.body)

    Sourcefile.to_file(fgen(routine), Path(pathw+".F90"))
#*********************************************************
#*********************************************************
#*********************************************************
#       Calling  the       transformation
#*********************************************************
#*********************************************************
#*********************************************************

parallel_trans()
#namearg=sys.argv[1]
#namearg=namearg.replace(".F90", "")
#Sourcefile.to_file(source.to_fortran(), Path(namearg+"_out.F90"))

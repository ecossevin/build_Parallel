import sys
from loki import *
from pathlib import Path
import re
import json

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
    Changes NPROMA arrays into field api objects : change dcls and add new dcls, field creation and field deletion
    :param dcls: dict of NRPOMA arrays declarations to change.
    :param lst_horizontal_size: lst of possible horizontal size names.
    :param map_dim: map_dim[0] : old_var : new_var+dim 
		    map_dim[1] : old_var : new_var+dim if derive_type; old_va+dim elif array
    """
#*******        ****************************************************
                        #LOCAL VARS of the caller, stored in dcls
                        #local var Z => PT Z,YL_Z
                        #build an array with the name of the arrays that were changed, replace the arrays gradually
                        #field_new_lst : creation of the field api objects
			#dfield_new_lst : deletion of the field api objects
#*******        ************************************************
    verbose=False
    #verbose=True
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',0,ZHOOK_HANDLE_FIELD_API)")
    field_new_lst=() #creation of objects
    field_new_lst=field_new_lst+new_node
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('DELETE_TEMPORARIES',0,ZHOOK_HANDLE_FIELD_API)")
    dfield_new_lst=() #deletion of objects
    dfield_new_lst=dfield_new_lst+new_node

    for dcl in dcls:
        var_dcl=dcls[dcl]
        var=var_dcl.symbols[0]
        var_routine=var
        d = len(var.dimensions)+1 #FIELD_{d}RB
        dd = d*":,"
        dd = dd[:-1]
        map_dim[0][var.name]="YL_"+var_routine.name+"("+dd+")"
        map_dim[1][var.name]=var_routine.name+"("+dd+")"
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
                lbound=lbound+"0, "
 
        ubound=ubound[:-2]+']' #rm last coma and space
        lbound=lbound[:-2]+']' #rm last coma and space
        if not is_lbound:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, PERSISTENT=.TRUE.)"
        else:
            field_str=f"CALL FIELD_NEW (YL_{var_routine.name}, UBOUNDS={ubound}, LBOUNDS={lbound}, PERSISTENT=.TRUE.)"
        dfield_str=f"IF (ASSOCIATED (YL_{var_routine.name})) CALL FIELD_DELETE (YL_{var_routine.name})"
        if verbose: print("field_str= ", field_str) 
        field_node=irgrip.slurp_any_code(field_str)
        dfield_node=irgrip.slurp_any_code(dfield_str)
        field_new_lst=field_new_lst+field_node
        dfield_new_lst=dfield_new_lst+dfield_node
        
  
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('CREATE_TEMPORARIES',1,ZHOOK_HANDLE_FIELD_API)")
    field_new_lst=field_new_lst+new_node
    routine.body.insert(2, field_new_lst) #insert at 1 => after first LHOOK 
    new_node=irgrip.slurp_any_code("IF (LHOOK) CALL DR_HOOK ('DELETE_TEMPORARIES',1,ZHOOK_HANDLE_FIELD_API)")
    dfield_new_lst=dfield_new_lst+new_node
    routine.body.insert(-2, dfield_new_lst) #insert at -1 => after last LHOOK 

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

def generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type):  
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
        str_data=generate_get_data(region_arrays, "DEVICE", "GET_DATA", subname, name)
    else:
        str_data=generate_get_data(region_arrays, "HOST", "GET_DATA", subname, name)
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
    strsynchost=generate_get_data(region_arrays, "HOST", "SYNCHOST", subname, name)
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

def generate_variables(args, str_body, map_dim):
    """
    Change variables of the region : add JBLK and change var name.
    :param map_dim: map_dim[0] : old_var : new_var+dim 
		    map_dim[1] : old_var : new_var+dim if derive_type; old_var+dim elif array

    """ 
    verbose=False


    def find_arg(string, arg_name, regex):
#        match=re.search(regex, string, flags=re.MULTILINE)
        match=re.finditer(regex, string, flags=re.MULTILINE)
        return(match)

    for arg in args: 
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            if arg.name in map_dim[1]:
                regex="(\\b"+fgen(arg.name)+"\\b)(\s*\([^)]*\))*"
                new_arg=map_dim[1][arg.name]
                new_arg_name=re.match("[a-zA-Z0-9_%]+", new_arg) #can use region_arrays to have directly name without dimensions...
                iter_match=find_arg(str_body, arg.name, regex)
                
                if not iter_match:
                    bprint("NO MATCH")
                else:
                    for match in reversed(list(iter_match)):
                        begin, end = match.start(), match.end()
                        if match.group(2): #if array already has some shapes: keep them and add JBLK at the end.
                            new_arg_dim=match.group(2)[:-1]+",JBLK)"
                            new_arg=new_arg_name.group(0)+new_arg_dim
                            if verbose: print("new_arg=", new_arg)
                          #  str_body=re.sub(regex, new_arg, str_body)
                            str_body = str_body[:begin]+new_arg+str_body[end:]
                        else: #if array has no shape : add them and add JBLK
                            new_arg=map_dim[1][arg.name].replace(":)","JBLK)")
                         #   str_body=re.sub(regex, new_arg, str_body)
                            str_body = str_body[:begin]+new_arg+str_body[end:]
    return(str_body+"\n")



#def generate_call(call, map_dim):
#    """
#    Changes call : add JBLK, change var name 
#    :param map_dim: map_dim[0] : old_var : new_var+dim 
#		    map_dim[1] : old_var : new_var+dim if derive_type; old_var+dim elif array
#
#    """
#    def find_arg(string, arg_name):
#        regex="(\\b"+arg.name+"\\b)(\s*\([^)]*\))*"
#        match=re.search(regex, string, flags=re.MULTILINE)
#        return(match)
#       
#    str_call=fgen(call)
#    for arg in call.arguments:
#        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
#            if arg.name in map_dim[1]:
#                new_arg=map_dim[1][arg.name]
#                new_arg_name=re.match("[a-zA-Z0-9_%]+", new_arg)
#                match=find_arg(str_call, arg.name)
#                if not match:
#                    bprint("NO MATCH")
#                if match.group(2): #if array already has some shapes: keep them and JBLK at the end.
#                    new_arg_dim=match.group(2)[:-1]+",JBLK)"
#                    new_arg=new_arg_name.group(0)+new_arg_dim
#                    print("new_arg=", new_arg)
#                    str_call=re.sub(regex, new_arg, str_call)
#                else: #if array has no shape : add them and add JBLK
#                    new_arg=map_dim[1][arg.name].replace(":)","JBLK)")
#                    str_call=re.sub(regex, new_arg, str_call)
#    return(str_call+"\n")
#
#def generate_non_call_args(args, lst_derive_type, str_body, map_dim):
#    """ 
#    Changes arrays that aren't in a call statement : 
#    """
##==========================================================    
##get non calls
##==========================================================    
#    regex=r'CALL[a-zA-Z0-9\s%_]*\((?:(?!CALL\().|\n)*?\)'
#    segs=re.split(regex, str_body)
#    non_calls=[seg.strip() for seg in segs if seg.strip() != '']
#    if non_calls:
#        for non_call in non_calls:
#            generate_call(non_calls, map_dim)
##            non_call_old=non_call
##            for arg in args:
##                if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
##                    if arg.name in lst_derive_type: #if 
##                        match=re.match("[\w%]+", map_dim[1][arg.name])
##                        if match: #arg in map_dim 
##                            new_name=match.group(0)
##                            regex=arg.name+"\([,:\w%\s]+\)" #match arg(JL, A%SSS, :)... 
##                            match_arg=re.search(regex, non_call, flags=re.MULTILINE) #match arg, if arg in non_call 
##                            if match_arg:
##                                old_arg=match_arg.group(0)
##                                #print("old_arg =", old_arg)
##                                regex="([\w%]+)(\([,:\w%\s]+\))"
##                                new_arg=old_arg[:-1]+", JBLK)"
##                                #print("old_arg =", old_arg)
##                                #print("new_arg =", new_arg)
##
##                                non_call=non_call.replace(old_arg, new_arg)
##                                #print("non_call=", non_call)
##                                
##                                #str_body=str_body.replace(arg.name
##                                #>>>TODO : ADD JBLK
#        str_body=str_body.replace(non_call_old, non_call)
##  #      print("str_body = ", str_body)
##    else:
##        print("no non-calls")
#    return(str_body)    

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

   def change_jl_loop(str_region, acc=None):
      if acc:
           code=acc
      else:
           code=""
      
      
      str_jlon="DO JLON = 1, MIN (YDCPG_OPTS%KLON, YDCPG_OPTS%KGPCOMP - (JBLK - 1) * YDCPG_OPTS%KLON)\n"
      str_jlon=code+str_jlon
      code="YLCPG_BNDS%KIDIA = JLON\n"
      str_jlon=str_jlon+code
      code="YLCPG_BNDS%KFDIA = JLON\n"
      str_jlon=str_jlon+code
      code="YLSTACK%L = stack_l (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
      str_jlon=str_jlon+code
      code="YLSTACK%U = stack_u (YSTACK, JBLK, YDCPG_OPTS%KGPBLKS)\n"
      str_jlon=str_jlon+code
      regex="DO JLON.*"
      str_region=re.sub(regex,str_jlon, str_region) #insert in str_region, at line DO JLON =, str_jlon
      return(str_region)
 
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
       code=f"""
            !&ACC LOOP VECTOR &\n
            !$ACC&PRIVATE ({private})\n"""
       return(str_openaccscc, code)

   str_region=fgen(region.body)
   str_jlon=["DO JLON=YDCPG_BNDS%KIDIA,YDCPG_BNDS%KFDIA", "ENDDO"]
   str_region=add_lines(str_region, str_jlon) #add JLON loops around CALL statements
   generate_call(calls, str_region) #add _OPENACC and YDSTACK
   str_region=generate_variables(args, str_region, map_dim) #change variables (YL->Z_YL; +dim + JBLK)
   if parallelmethod=="OPENMPSINGLECOLUMN":
       str_scc=generate_pragma_openmpscc(region_scalar)
       code_acc = ""
   elif parallelmethod=="OPENACCSINGLECOLUMN":
       str_scc, code_acc=generate_pragma_openaccscc(region_arrays, region_scalar)
   str_region=change_jl_loop(str_region, code_acc)
   str_scc=str_scc+str_region+"\n"

   code="ENDDO\n"
   str_scc=str_scc+code
   
  
   return(str_scc)

def generate_call(calls, str_body):
    """
    Changes the calls in calls : add _OPENACC to their name and YDSTACK=YLSTACK to the routine args.
    :param calls: calls of the parallel region : calls=FindNodes(CallStatement).visit(region)
    :param str_body: string of region
    """
    for call in calls:
        str_call=fgen(call)
        regex="CALL\s"+fgen(call.name)
        call_name=re.match(regex, str_call).group(0)
        str_call=str_call.replace(call_name, call_name+"_OPENACC")
        str_call=str_call[:-2]+", YDSTACK=YLSTACK)\n"
        regex="CALL\s"+fgen(call.name)+"\([a-zA-Z0-9_%&\s:,\(\)]*\)"
        str_body=re.sub(regex,str_call, str_body) #insert in str_body, at line DO JLON =, str_jlon




    
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
    :param routine:.
    :param field_index: index of field api struct members 
    :param region_arrays: mapping of names. region_arrays[Z_...]=YL_Z...; region_arrays[Z_A_B_C...]=A%B%C
    :param region_scalar
    :param ???
    :param lst_derive_type: lst of derived type that were already added to the routine spec
#######    :param dcls: maps the derive type name with its declaration in order to insert new dcl node at theright place
    """
    verbose=False
    #verbose=True
#    for arg in call.arguments:
    for arg in args:
        if verbose: print("arg = ",  arg)
        #arg can be logical and/or: "YDCPG_OPTS%YRSURF_DIMS%YSD_VVD%NUMFLDS>=8.AND.YDMODEL%YRML_PHY_MF%YRPHY"
        if not (isinstance(arg, symbols.LogicalOr) or isinstance(arg, symbols.LogicalAnd)):
            arg_name=arg.name
            if '%' in arg_name: # 1) derive_type already on lst_derive_type, 2) derive_type in index, 3) derive_type CPG_OPTS_TYPE 
                arg_basename=arg_name.split("%")[0]
                var_routine=routine.variable_map[arg_basename]
                if var_routine.type.dtype.name=="MF_PHYS_SURF_TYPE": #remove P
#                    p_arg=arg_name.split("%")[-1:][0][1:]
                    arg_name__="%".join(arg_name.split("%")[:-1])+"%F_"+arg_name.split("%")[-1:][0][1:] #remove extra P
                else:
                    arg_name__="%".join(arg_name.split("%")[:-1])+"%F_"+arg_name.split("%")[-1:][0] #A%B%C => A%B%F_C
                #arg_name__=arg_name
                arg_name_=arg_name_='%'.join(arg_name.split("%")[1:])
#                print("var_routine = ", var_routine)
#                print("var_routine.type.dtype = ", var_routine.type.dtype)
#                print("type(var_routine.type.dtype) = ", type(var_routine.type.dtype))
                if arg_name__ in lst_derive_type: #1) derive_type already on lst_derive_type
                    new_name="Z_"+arg_name.replace("%","_")
                    region_arrays[new_name]=arg_name__ #????
                    if verbose:
                        print(" ************ 1 adding var to region_arrays   ****************") 
                        print("arg_name= ",  arg_name)
                        print("new_name  = ",  new_name)
                        print(" *************************************************************") 
                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                elif (var_routine.type.dtype.name+"%"+arg_name_ in field_index): #2) derive_type in index 
                #elif arg_name in var_routine.type.dtype.name+"%"+arg_name_ in field_index: #2) derive_type in index 
                    new_name="Z_"+arg_name.replace("%","_")
                    region_arrays[new_name]=arg_name__
                    if verbose:
                        print(" ************ 2 adding var to region_arrays   ****************") 
                        print("new_name",  new_name)
                        print(" *************************************************************") 

                    new_arg=arg.clone(name=new_name) #TODO :::::: BOUNDS!!!!!!!!! with blcks!
                    lst_derive_type.append(arg_name__)
                    key=var_routine.type.dtype.name+'%'+arg_name_
                    new_var_type = field_index[key][0] 
                    d=field_index[key][1][:-1]+",:)"
                    dd=re.match("([A-Z0-9]*)(.*)", d)
                    new_var_name= 'Z_'+'_'.join(arg_name.split("%")[:-1])+'_'+d  #A%B%C => A%B%C(:,:,:)
                    map_dim[0][arg_name]=new_var_name
                    map_dim[1][arg_name]=new_var_name
                    new_var=irgrip.slurp_any_code(f"{new_var_type}, POINTER :: {new_var_name}")
                    routine.spec.insert(-1, new_var)
                elif (var_routine.type.dtype in ["CPG_OPTS_TYPE"]):
                #elif (var_routine.type.dtype.upper() in ["CPG_OPTS_TYPE"]):
                    #TODO
                    if verbose: print("Var : ", var_routine, " is of type CPG_OPTS_TYPE.")
                else: #derive_type not field_api and not CPG_OPTS_TYPE                               
                    if verbose: 
                        print("====================================================================")
                        print("Argument = ", arg_name, "not in field api index, neither CPG_OPTS_TYPE!!!")
                        print("====================================================================")
    
            else: 
                if arg.name in dcls:
                    arg_name=arg.name
                    region_arrays[arg_name]="YL_"+arg_name #region_arrays[Z_A]=YL_ZA
                    if verbose:
                        print(" ************ 3 adding var to call_arrays   ****************") 
                        print("arg_name= ",  arg_name)
                        print(" *************************************************************") 

                if isinstance(arg, Scalar):
                    region_scalar.append(arg_name)
        else: #if call arg is logical or/and
            print("Argument = ", arg_name, "ignored, logical statement")


def generate_lhook(subname, name, area1, area2, n):
    hookcode="IF (LHOOK) CALL DR_HOOK ('{subname}:{name}:{area1}',{n},ZHOOK_HANDLE_{area2})\n"
    return(hookcode)

def lhook(area, n, handle):
    hookcode=f"IF (LHOOK) CALL DR_HOOK ('{area}',{n},ZHOOK_HANDLE_{handle})\n"
    return(hookcode)
def generate_get_data(region_arrays, machine, area, subname, name):
    """
    machine : HOST or  DEVICE
    region_arrays : var of the call of the region.  #lhs => get_data(rhs) : region_arrays[lhs]=rhs
    intent[lhs] : RDWR or RDONLY for lhs
    area: GET_DATA or SYNCHOST
    """
    verbose=False
    str_get_data=""
    #codetarget=f"IF (LPARALLELMETHOD ('{target}','{subname}:{name}')) THEN\n" #"{target}_SECTION" is replaced by code 
    #str_get_data=str_get_data+codetarget
    strhook=f"{subname}:{name}:{area}"
    hookcode=lhook(strhook, "0", "FIELD_API")
    str_get_data=str_get_data+hookcode
    for var in region_arrays: #lhs => get_data(rhs) : region_arrays[lhs]=rhs
        lhs=var
        if verbose: print("region_arrays[lhs]  = ",  region_arrays[lhs])
        #============================================================
        #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({region_arrays[lhs]})\n"
        #          TODO INTENT => get interface and check intent of var
        #datacode=f"{lhs} => GET_{machine}_DATA_{intent[lhs]} ({region_arrays[lhs]})\n"
        #============================================================
        #field=region_arrays[lhs]
        #field_="%".join(field.split("%")[:-1])+"%F_"+field.split("%")[-1:] # A%B%C => A%B%F_C
        #datacode=f"{lhs} => GET_{machine}_DATA_RDWR ({field_})\n"
        datacode=f"{lhs} => GET_{machine}_DATA_RDWR ({region_arrays[lhs]})\n"
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
                #print("#########################################################")
                #print("#########################################################")
                #print("#########################################################")
                #print("##                    ROUTINE    SPEC                  ##")
                #print(fgen(routine.spec))
                #print("#########################################################")
                #print("#########################################################")
                #print("#########################################################")
                stop=True
            break
        if stop:
            break

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
#path_irgrip="/home/cossevine/kilo/src/kilo"
path_irgrip="/home/gmap/mrpm/cossevine/kilo/src/acdc/loki"
sys.path.append(path_irgrip)
import irgrip

import logical_lst
import logical
import pickle
import loop_fusion

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

    #----------------------------------------------
    #setup
    #----------------------------------------------
#    verbose=True
    verbose=False
    print("pathpack =", pathpack)
    print("pathview =", pathview)
    print("pathfile =", pathfile)
    
    pathr=pathpack+'/'+pathview+pathfile

    pathw=pathr.replace(".F90", "")+"_parallel"
    
    if verbose: print('pathr=', pathr)
    if verbose: print('pathw=', pathw)
    import logical_lst
    #exit(1)
    #
    
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
    #----------------------------------------------
    #transformation:
    #----------------------------------------------
    lst_horizontal_size=["KLON","YDCPG_OPTS%KLON","YDGEOMETRY%YRDIM%NPROMA","KPROMA", "YDDIM%NPROMA", "NPROMA"]
    true_symbols, false_symbols = logical_lst.symbols()
    #false_symbols.append('LHOOK')
    
    with open(pathpack+'/'+'field_index.pkl', 'rb') as fp:
        field_index= pickle.load(fp)
    map_dim=[{},{}] #map_dim[old_field]=new_field(:,:,;...)
    lst_derive_type=[] #store derive types that are added to the routine spec
#    for routine in source.routines:
    routine=source.subroutines[0]    
    logical.transform_subroutine(routine, true_symbols, false_symbols)
    resolve_associates(routine)

    add_var(routine)
    dcls=get_dcls(routine, lst_horizontal_size)
    change_arrays(routine, dcls, lst_horizontal_size, map_dim)
    #dcls=[ decl for decl in FindNodes(VariableDeclaration).visit(routine.spec)]
    need_field_api = set()
    routine_name = routine.name + "_PARALLEL"
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
    #new_routine_name = routine.name + "_PARALLEL"
    regions=GetPragmaRegionInRoutine(routine)
    PragmaRegions=FindNodes(PragmaRegion).visit(routine.body)
    for i in range(len(regions)):
   #     print(regions[i])
   #     print(i)
        region=regions[i]
        Pragma=PragmaRegions[i]
   #      print("region", routine.name)
        calls=[call for call in FindNodes(CallStatement).visit(region["region"])]

        #loops_klev=[loop for loop in FindNodes(ir.Loop).visit(region["region"]) if loop.variable=="JLEV"]
        
        #loops_jlon=[loop for loop in FindNodes(ir.Loop).visit(region["region"]) if loop.variable=="JLON"]
        
        name=region['name']
        subname=routine.name
        new_args = dict()
        targets=region["targets"]
        region=region["region"]
        region_arrays={}
        region_scalar=[]
  
   
    
        args=FindVariables(unique=True).visit(region)
        
        do_call=True
        if do_call:
             #for call in calls:
            compute_region(routine, args, field_index, region_arrays, region_scalar, lst_derive_type, map_dim, lst_horizontal_size, dcls)
   #             args_callee = get_callee_args_of(call.name)
            if len(calls) >1:
                print(" ************************ CAUTION MORE THAN ONE CALL IN A REGION  *****************")
            code_region=""
            if verbose: print("targets = ", targets)
            for target in targets: 
            #for target in region['targets']:
   #            print("target = ", target)
               able_mp=True
               able_scc=True
               #able_scc=False
               #able_acc=False
               able_acc=True
               
               if target=='OpenMP' and able_mp:
   #                print("*****OpenMPEN MP ******")
                   parallelmethod="OPENMP"
                   str_openmp=generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type)
                   node_openmp=irgrip.slurp_any_code(str_openmp)
                   #print("region_arrays = ",  region_arrays)
                   if verbose:
                       print(str_openmp)
                       print("=================================================================")
                       print("======================== fgen ======================")   
                       print("=================================================================")
                       print(fgen(node_openmp))
           #        print(fgen(node_openmp))
           #        file11=open("nodemp.txt", "w")
           #        file11.write(str_openmp)
           #        file11.close()
            #       exit(1)
                   code_region=code_region+str_openmp
                   #code_target=code_target+f"\n"+str_openmp
               elif target=="OpenMPSingleColumn" and able_scc:
                   #print("*****OpenMPEN MPSCC ******")
                   parallelmethod="OPENMPSINGLECOLUMN"
                   str_openmpscc=generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type)
                   node_openmpscc=irgrip.slurp_any_code(str_openmpscc)
                   if verbose:
                       print(str_openmpscc)
                       print("=================================================================")
                       print("======================== fgen open mp scc  ======================")
                       print("=================================================================")
                       print(fgen(node_openmpscc))
                   code_region=code_region+str_openmpscc
                   #code_target=code_target+f"\n"+str_openmpscc
   
               elif target=="OpenACCSingleColumn" and able_acc:
                   #print("*****OpenAccSCC ******")
                   parallelmethod="OPENACCSINGLECOLUMN"
                   str_openaccscc=generate_parallelregion(region, calls, map_dim, region_arrays, parallelmethod, subname, name, args, region_scalar, lst_derive_type)
                   node_openaccscc=irgrip.slurp_any_code(str_openaccscc)
                   #print(str_openaccscc)
                   #print("=================================================================")
                   #print("======================== fgen open acc scc  =====================")
                   #print("=================================================================")
                   #print(fgen(node_openaccscc))
                   code_region=code_region+str_openaccscc
                   #code_target=code_target+f"\n"+str_openaccscc
#             print("******************************************************") 
#             print("******************************************************") 
#             print("******************************************************") 
#             print("               ROUTINE                ")
#             print("******************************************************") 
#             print("******************************************************") 
#             print(code_region)
#             print("******************************************************") 
#             print("******************************************************") 
#             print("******************************************************") 
#             print("     FGEN          ROUTINE                ")
#             print("******************************************************") 
#             print("****************************
#             print(fgen(code_region))

            #breakpoint()
            print("code_region =", code_region)
            node_target=irgrip.slurp_any_code(code_region)
            routine.body=irgrip.insert_at_node(Pragma, node_target, rootnode=routine.body)

    #print(" ============================================")
    #print(" ============================================")
    #print(" ============================================")
    #print("             FINAL    FGEN       ") 
    #print(" ============================================")
    Sourcefile.to_file(fgen(routine), Path(pathw+".F90"))
    #Sourcefile.to_file(to_fortran(), Path(pathw+".F90"))
    #Sourcefile.to_file(source.to_fortran(), Path(pathw+".F90"))
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

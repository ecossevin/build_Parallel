
import re
from loki import *
#loops_jlon=[FindNodes(ir.Loop).visit(loop.body) for loop in loops_jlev]
#print("loops_jlev= ", loops_jlev)
#print("loops_jlon= ", loops_jlon)
#print(loops)
#for loop_jlev in loops_jlon:
#    for loop_jlon in loop_jlev:
#        if loop_jlon.variable!="JLON":
#            print("Caution, var = ", loop.variable, " isn't JLON.")

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
        pragma_regions.append({"region": region, "targets": targets, "name": name})
    return pragma_regions

def reverse_loops(region):
    loops=[loop for loop in FindNodes(ir.Loop).visit(region)]
    loops_jlev=[loop for loop in loops if loop.variable=="JLEV"]

    loop_map={}
    for loop_jlev in loops_jlev:
        loops_jlon=FindNodes(ir.Loop).visit(loop_jlev.body)
    #    for loop in loops_jlon:
    #        if loop.bounds
        outer_loop=loop_jlev
        loop_map[outer_loop]=()
        for loop_jlon in loops_jlon:
            inner_loop=loop_jlon
            new_inner_loop=outer_loop.clone(body=inner_loop.body)
            loop_map[outer_loop]+=(inner_loop.clone(body=(new_inner_loop,)),)
    #    print("loop_map = ", loop_map)
        
    region= Transformer(loop_map).visit(region)
    #routine.body = Transformer(loop_map).visit(routine.body)

    return(region)


def fuse_jlon(region):

    nodes = FindNodes((CallStatement,Loop)).visit(region.body)
    print("nodes = ", nodes)
    for node in nodes:
        if isinstance(node, Loop):
            inner_loops=FindNodes(Loop).visit(node.body)
          
            for inner_loop in inner_loops:
                if inner_loop in nodes:
    #                print("inner_loop in nodes")
                    nodes.remove(inner_loop)
                   # if inner_loop.variable=="JLON":
                   #     #loop inversion must be done before
                   #     print("======================================================")
                   #     print("Caution, an inner loop is horizontal!!!")
                   #     print("======================================================")
                   # elif inner_loop.variable=="JLEV":
                   # else:
                   #     print("======================================================")
                   #     print("Caution, an inner loop isn't vertical!!!")
                   #     print("loop idx= ", inner_loop.variable)
                   #     print("======================================================")
    
    #Dans nodes : on veut fusionner tous les élements consécutifs avec comme idx JLON + bounds identiques
    #No hor dependencies in the phys
    NN=len(nodes)
    idx1=0
    jlloops=[]
    while idx1<NN: #look if JLON loops with same bounds from nodes[idx1] up to nodes[idx2]
        to_fuse=[]
        if isinstance(nodes[idx1], Loop):
            if nodes[idx1].variable=="JLON":
                idx_fuse=idx1
                bounds1=nodes[idx1].bounds
                for idx2 in range(idx_fuse,NN):
                    if isinstance(nodes[idx2], Loop):
    
                        if nodes[idx2].variable=="JLON":
                            bounds2=nodes[idx2].bounds
                            if bounds1==bounds2:
                                to_fuse.append(nodes[idx2])
                                #new_inner_loop=nodes[idx2].body
    #                            new_inner_loop=nodes[idx2].clone(body=nodes[idx2].body)
    #                            loop_map[nodes[idx_fuse]]+=inner_loop.clone(body=(new_
                                idx1=idx2+1
                            else: #if next loop has same idx but diff bounds
                                idx1=idx2
                                break #OR CALL SMTHG TO NORMALIZE IDX...
                        else: #if next loop is on a diff idx
                            idx1=idx2+1
                            break
    
                    elif isinstance(nodes[idx2], CallStatement): #if next node isn't loop, but is call statement : include CALL in JLON loop : CALL SUB_OPENACC
                        to_fuse.append(nodes[idx2])
                        idx1=idx2+1 
    #========================================================================================
    #========================================================================================
                    else: #if next node isn't loop, can't fuse : maybe wrong in some places :TODO => CHECK/ASK THAT 
    #========================================================================================
    #========================================================================================
                        idx1=idx2+1 #start exploration at the next element
                        break

                jlloops.append(to_fuse) 
            
            else:
                idx1+=1 #not a JLON loop 
        else:
            idx1+=1 #not a loop
    #            print("to_fuse= ", to_fuse)
    #            for loop in to_fuse:
    #                print("loop_body = ", loop.body)
    loop_map={}
    for to_fuse in jlloops:
        loop_body=flatten([loop.body for loop in to_fuse])
        new_loop=Loop(variable=to_fuse[0].variable, body=loop_body, bounds=to_fuse[0].bounds)
        loop_map[to_fuse[0]]=new_loop
        loop_map.update({loop: None for loop in to_fuse[1:]})
#    print(loop_map)
    region = Transformer(loop_map).visit(region)
    return(region)


#def fuse_jlon_old(region):
#
#    nodes = FindNodes((CallStatement,Loop)).visit(region.body)
#    print("nodes = ", nodes)
#    for node in nodes:
#        if isinstance(node, Loop):
#            inner_loops=FindNodes(Loop).visit(node.body)
#          
#            for inner_loop in inner_loops:
#                if inner_loop in nodes:
#    #                print("inner_loop in nodes")
#                    nodes.remove(inner_loop)
#                   # if inner_loop.variable=="JLON":
#                   #     #loop inversion must be done before
#                   #     print("======================================================")
#                   #     print("Caution, an inner loop is horizontal!!!")
#                   #     print("======================================================")
#                   # elif inner_loop.variable=="JLEV":
#                   # else:
#                   #     print("======================================================")
#                   #     print("Caution, an inner loop isn't vertical!!!")
#                   #     print("loop idx= ", inner_loop.variable)
#                   #     print("======================================================")
#    
#    #Dans nodes : on veut fusionner tous les élements consécutifs avec comme idx JLON + bounds identiques
#    #No hor dependencies in the phys
#    NN=len(nodes)
#    idx1=0
#    jlloops=[]
#    while idx1<NN: #look if JLON loops with same bounds from nodes[idx1] up to nodes[idx2]
#        to_fuse=[]
#        if isinstance(nodes[idx1], Loop):
#            if nodes[idx1].variable=="JLON":
#                idx_fuse=idx1
#                bounds1=nodes[idx1].bounds
#                for idx2 in range(idx_fuse,NN):
#                    if isinstance(nodes[idx2], Loop):
#    
#                        if nodes[idx2].variable=="JLON":
#                            bounds2=nodes[idx2].bounds
#                            if bounds1==bounds2:
#                                to_fuse.append(nodes[idx2])
#                                #new_inner_loop=nodes[idx2].body
#    #                            new_inner_loop=nodes[idx2].clone(body=nodes[idx2].body)
#    #                            loop_map[nodes[idx_fuse]]+=inner_loop.clone(body=(new_
#                                idx1=idx2+1
#                            else: #if next loop has same idx but diff bounds
#                                idx1=idx2
#                                break #OR CALL SMTHG TO NORMALIZE IDX...
#                        else: #if next loop is on a diff idx
#                            idx1=idx2+1
#                            break
#    
#    #========================================================================================
#    #========================================================================================
#                    else: #if next node isn't loop, can't fuse : maybe wrong in some places :TODO => CHECK/ASK THAT 
#    #========================================================================================
#    #========================================================================================
#                        idx1=idx2+1 #start exploration at the next element
#                        break
#                jlloops.append(to_fuse) 
#            
#            else:
#                idx1+=1 #not a JLON loop 
#        else:
#            idx1+=1 #not a loop
#    #            print("to_fuse= ", to_fuse)
#    #            for loop in to_fuse:
#    #                print("loop_body = ", loop.body)
#    loop_map={}
#    for to_fuse in jlloops:
#        loop_body=flatten([loop.body for loop in to_fuse])
#        new_loop=Loop(variable=to_fuse[0].variable, body=loop_body, bounds=to_fuse[0].bounds)
#        loop_map[to_fuse[0]]=new_loop
#        loop_map.update({loop: None for loop in to_fuse[1:]})
##    print(loop_map)
#    region = Transformer(loop_map).visit(region)
#    return(region)

#path="/home/cossevine/build_Parallel/src/toto2.F90"
#file=Sourcefile.from_file(path)
#routine=file["APL_ARPEGE"]
#loops=[loop for loop in FindNodes(ir.Loop).visit(routine.body)]
#loops_jlev=[loop for loop in loops if loop.variable=="JLEV"]

#regions=GetPragmaRegionInRoutine(routine)
#region=regions[0]["region"]
def loops_fusion(region):
    region=reverse_loops(region)
    region=fuse_jlon(region)
    return(region)
#region=loop_fusion(region)
#print(fgen(region))
#TODO:
#loops = FindNodes((Loop)).visit(region)
#
#
#map_loop_outer={}
#for loop in loops:
#    inner_loop=FindNodes(Loop).visit(loop.body)
#    if inner_loop:
#        map_loop_outer[loop]=inner_loop
#        loop_outer.append(loop)
#print("map_loop_outer = ", map_loop_outer)
#print(fgen(region))
#
#nodes = FindNodes((CallStatement,Loop)).visit(region)
#        
##print(fgen(routine.body))        
#
##print(routine.body.children)

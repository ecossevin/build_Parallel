
import re
from loki import *
path="/home/cossevine/build_Parallel/src/toto2.F90"
file=Sourcefile.from_file(path)
routine=file["APL_ARPEGE"]
loops=[loop for loop in FindNodes(ir.Loop).visit(routine.body)]
loops_jlev=[loop for loop in loops if loop.variable=="JLEV"]
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
    	# print(fgen(region))
        pragma_regions.append({"region": region, "targets": targets, "name": name})
    return pragma_regions

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
    
routine.body = Transformer(loop_map).visit(routine.body)


regions=GetPragmaRegionInRoutine(routine)
region=regions[0]["region"]

nodes = FindNodes((CallStatement,Loop)).visit(region)

for node in nodes:
    if isinstance(node, Loop):
        if not FindNodes(Loop).visit(node.body):
            if node.variable=="JLON":
                #loop inversion must be done before
                print("======================================================")
                print("Caution, an inner loop is horizontal!!!")
                print("======================================================")
            nodes.remove(node) #remove inner loops
        print(node)
print("nodes= ", nodes)
#Dans nodes : on veut fusionner tous les élements consécutifs avec comme idx JLON + bounds identiques
NN=len(nodes)
print("NN = ", NN)
#for idx1=1,NN:
idx1=0
while idx1<NN:
    if isinstance(nodes[idx1], Loop):
        if nodes[idx1].variable=="JLON":
            bounds1=nodes[idx1].bounds
            to_fuse=[nodes[idx1]]
            for idx2 in range(idx1,NN):
                if isinstance(nodes[idx2], Loop):

                    if nodes[idx2].variable=="JLON":
                        bounds2=nodes[idx2].bounds
                        if bounds1==bounds2:
                            to_fuse.append(nodes[idx2])
                            idx1=idx2+1
                        else: #if next loop has same idx but diff bounds
                            idx1=idx2
                            break #OR CALL SMTHG TO NORMALIZE IDX...
                    else: #if next loop is on a diff idx
                        idx1=idx2+1
                        break

#========================================================================================
#========================================================================================
                else: #if next node isn't loop, can't fuse : maybe wrong in some places :TODO => CHECK/ASK THAT 
#========================================================================================
#========================================================================================
                    idx1=idx2+1 #start exploration at the next element
                    break
           
print(to_fuse)
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

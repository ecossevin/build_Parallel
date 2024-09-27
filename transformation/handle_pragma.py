import re

from loki import *

def extract_pragma_region(ir, start, end):
#from loki commit dc997800a60c66d56dfa8e90cf5edb8c1577d4ad
    """
    Create a :any:`PragmaRegion` object defined by two :any:`Pragma` node
    objects :data:`start` and :data:`end`.

    The resulting :any:`PragmaRegion` object will be inserted into the
    :data:`ir` tree without rebuilding any IR nodes via ``Transformer(...,
    inplace=True)``.
    """
    assert isinstance(start, Pragma)
    assert isinstance(end, Pragma)

    # Pick out the marked code block for the PragmaRegion
    block = MaskedTransformer(start=start, stop=end, inplace=True).visit(ir)
    block = as_tuple(flatten(block))[1:]  # Drop the initial pragma node
    region = PragmaRegion(body=block, pragma=start, pragma_post=end)

    # Remove the content of the code region and replace
    # starting pragma with new PragmaRegion node.
    mapper = {}
    for node in block:
        mapper[node] = None
    mapper[start] = region
    mapper[end] = None

    return Transformer(mapper, inplace=True).visit(ir)

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

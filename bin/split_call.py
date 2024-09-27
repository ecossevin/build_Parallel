
call = "NAME(A, B,C%sdfdfd//k,  D_totoedSS  , E )"
call1 = """CALL RECMWF_PARALLEL (YDGEOMETRY, YDGEOMETRY%YRDIMV, YDMODEL, YDCPG_OPTS, YDCPG_BNDS, YDMODEL%YRML_PHY_RAD&
%YRERAD%NOZOCL, YDMODEL%YRML_PHY_RAD%YRERAD%NAERMACC, IAERO, YD_PALBD, YD_PALBP, YDMF_PHYS_BASE_STATE&
%YCPG_PHY%F_PREHYD, YDMF_PHYS_BASE_STATE%YCPG_PHY%F_PREHYDF, YDCPG_MISC%F_NEB, YD_PQO3, YL_ZDUM&
, YL_ZDUM, YL_ZDUM, YL_ZDUM, YL_ZDUM, YL_ZDUM, YL_ZDUM, YL_ZDUM, YD_PAER, YL_ZAERO, YL_ZAEROCPL&
, YDMF_PHYS_BASE_STATE%YCPG_PHY%XYB%F_DELP, YD_PFLU_EMIS, YD_PRDG_MU0M, YD_PQV, YD_PFLU_QSAT,&
 YDCPG_MISC%F_QICE, YDCPG_MISC%F_QLI, YD_PQS, YD_PQR, YDMF_PHYS_SURF%GSD_VF%F_LSM, YDMF_PHYS_BASE_STATE&
%F_T, YDMF_PHYS_BASE_STATE%YGSP_RR%F_T, YDVARS%RADIATION%EMTD%FT0, YDVARS%RADIATION%EMTU%FT0,&
 YDVARS%RADIATION%TRSW%FT0, YDMF_PHYS%OUT%F_FRTHC, YDMF_PHYS%OUT%F_FRTH, YDMF_PHYS%OUT%F_FRSOC&
, YDMF_PHYS%OUT%F_FRSO, YD_PSFSWDIR, YD_PSFSWDIF, YL_ZFSDNN, YL_ZFSDNV, YD_PCTRSO, YD_PCEMTR,&
 YD_PTRSOD, YD_PTRSODIR, YD_PTRSODIF, YL_ZPIZA_DST, YL_ZCGA_DST, YL_ZTAUREL_DST, YD_PAERINDS,&
 YDVARS%GEOMETRY%GELAM%FT0, YDVARS%GEOMETRY%GEMU%FT0, YDCPG_GPAR%F_SWDIR, YDCPG_GPAR%F_SWDIF,&
 YD_PRDG_MU0LU, YDMF_PHYS%OUT%F_ALB, YDVARS%RADIATION%RMOON%FT0) 
"""

call2="""SUBROUTINE RECMWF_PARALLEL (YDGEOMETRY, YDDIMV, YDMODEL, YDCPG_OPTS, YDCPG_BNDS, KOZOCL, KMACCAERO, KAERO&
, YD_PALBD, YD_PALBP, YD_PAPRS, YD_PAPRSF, YD_PNEB, YD_PQO3, YD_PQCO2, YD_PQCH4, YD_PQN2O,&
 YD_PQNO2, YD_PQC11, YD_PQC12, YD_PQC22, YD_PQCL4, YD_PAER, YD_PAERO, YD_PAEROCPL, YD_PDELP&
, YD_PEMIS, YD_PMU0M, YD_PQ, YD_PQSAT, YD_PQICE, YD_PQLIQ, YD_PS, YD_PRR, YD_PLSM, YD_PT, YD_PTS&
, YD_PEMTD, YD_PEMTU, YD_PTRSO, YD_PLWFC, YD_PLWFT, YD_PSWFC, YD_PSWFT, YD_PSFSWDIR, YD_PSFSWDIF&
, YD_PFSDNN, YD_PFSDNV, YD_PCTRSO, YD_PCEMTR, YD_PTRSOD, YD_PTRSODIR, YD_PTRSODIF, YD_PPIZA_DST&
, YD_PCGA_DST, YD_PTAUREL_DST, YD_PAERINDS, YD_PGELAM, YD_PGEMU, YD_PSWDIR, YD_PSWDIF, YD_PMU0LU&
, YD_PALB, YD_PVRMOON, YD_PCLDROP, YSPP_RSWINHF, YSPP_RLWINHF)
"""

is_ampersand = False
def line_break(call_string):
    if is_ampersand:
        ampersand = "&"
    else:
        ampersand = ""
    call_name = call_string.split("(")[0].strip()
    call_params = call_string.replace(call_name, "")
    call_params = call_params.replace("(", "").replace(")", "").replace(" ","")
    lines = call_params.split(",")
    new_call = f"{call_name}( {ampersand} \n" 
    for line in lines: 
        new_call += ampersand + line.strip() + f", {ampersand} \n" 
    if is_ampersand:
        new_call = new_call[:-5]
    else: 
        new_call = new_call[:-4]
    new_call += ")"
    return new_call
print(line_break(call1))
print(line_break(call2))
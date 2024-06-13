SUBROUTINE CPPHINP_OPENACC (YDGEOMETRY, YDMODEL, KIDIA, KFDIA, PGEMU, PGELAM, PUT0, PVT0, PQT0, PQT0L&
&, PQT0M, PQSLT0L, PQSLT0M, PRDELP0, PEVEL0, PCVGQSL, PMU0, PMU0LU, PMU0M, PMU0N, PCVGQ, YDSTACK)
USE PARKIND1,ONLY:JPIM, JPRB
USE TYPE_MODEL,ONLY:MODEL
USE GEOMETRY_MOD,ONLY:GEOMETRY
USE STACK_MOD
IMPLICIT NONE
TYPE (GEOMETRY), INTENT (IN)::YDGEOMETRY
TYPE (MODEL), INTENT (IN)::YDMODEL
INTEGER (KIND=JPIM), INTENT (IN)::KIDIA
INTEGER (KIND=JPIM), INTENT (IN)::KFDIA
REAL (KIND=JPRB), INTENT (IN)::PGEMU (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (IN)::PGELAM (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (IN)::PUT0 (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PVT0 (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PQT0 (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PQT0L (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PQT0M (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PQSLT0L (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PQSLT0M (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PRDELP0 (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PEVEL0 (YDGEOMETRY%YRDIM%NPROMA, 0:YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (IN)::PCVGQSL (YDGEOMETRY%YRDIM%NPROMA, YDGEOMETRY%YRDIMV%NFLEVG)
REAL (KIND=JPRB), INTENT (OUT)::PMU0 (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (OUT)::PMU0LU (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (OUT)::PMU0M (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (OUT)::PMU0N (YDGEOMETRY%YRDIM%NPROMA)
REAL (KIND=JPRB), INTENT (OUT)::PCVGQ (YDGEOMETRY%YRDIM%NPROMM, YDGEOMETRY%YRDIMV%NFLEVG)
TYPE(STACK) :: YDSTACK
ENDSUBROUTINE CPPHINP_OPENACC

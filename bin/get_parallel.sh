#!/bin/bash

set -x
set -e

export PATH=/home/gmap/mrpm/cossevine/build_Parallel:$PATH
p=$(pwd)
echo $p

function resolve ()
{
  f=$1
  for view in $(cat .gmkview)
  do
    g="src/$view/$f"
    if [ -f $g ]
    then
#      echo $g
      echo "src/$view/"
      break
    fi
  done
}

for f in \
  arpifs/phys_dmn/apl_arpege_init.F90                                    \
  arpifs/phys_dmn/apl_arpege_init_surfex.F90                             \
  arpifs/phys_dmn/apl_arpege_oceanic_fluxes.F90                          \
  arpifs/phys_dmn/apl_wind_gust.F90                                      \
  arpifs/phys_dmn/mf_phys_mocon.F90                                      \
  arpifs/phys_dmn/apl_arpege_shallow_convection_and_turbulence.F90       \
  arpifs/phys_dmn/apl_arpege_albedo_computation.F90                      \
  arpifs/phys_dmn/apl_arpege_aerosols_for_radiation.F90                  \
  arpifs/phys_dmn/apl_arpege_cloudiness.F90                              \
  arpifs/phys_dmn/apl_arpege_radiation.F90                               \
  arpifs/phys_dmn/apl_arpege_soil_hydro.F90                              \
  arpifs/phys_dmn/apl_arpege_deep_convection.F90                         \
  arpifs/phys_dmn/apl_arpege_surface.F90                                 \
  arpifs/phys_dmn/apl_arpege_precipitation.F90                           \
  arpifs/phys_dmn/apl_arpege_hydro_budget.F90                            \
  arpifs/phys_dmn/apl_arpege_dprecips.F90                                \
  arpifs/phys_dmn/apl_arpege_atmosphere_update.F90                       \
  arpifs/adiab/cputqy_aplpar_expl.F90                                    \
  arpifs/adiab/acctnd0.F90                                               \
  arpifs/adiab/cputqy0.F90                                               \
  arpifs/phys_dmn/mf_phys_transfer.F90                                   \
  arpifs/phys_dmn/apl_arpege_surface_update.F90                          \
  arpifs/phys_dmn/apl_arpege.F90                                         \
  arpifs/phys_dmn/mf_phys_prep.F90                                       \
  arpifs/phys_dmn/mf_phys_init.F90                                       \
  arpifs/phys_dmn/mf_phys.F90                                            \
  arpifs/phys_dmn/mf_phys_save_phsurf_part2.F90                          \
  arpifs/phys_dmn/mf_phys_save_phsurf_part1.F90                          \
  arpifs/phys_dmn/mf_phys_fpl_part2.F90                                  \
  arpifs/phys_dmn/mf_phys_fpl_part1.F90                                  \
  arpifs/phys_dmn/acvppkf.F90
do

#f=arpifs/phys_dmn/apl_arpege.F90

echo "==> $f <=="
dir=$(dirname $f)
g=$(resolve $f)
mkdir -p test/parallel/$dir
mkdir -p test/src/$dir
cp $g/$f test/src/$f
parallel=$(basename $f .F90)_parallel.F90
#parallelint=$(basename $f .F90)_parallel.intfb.h
cp src/main/$dir/$parallel test/parallel/$dir/$parallel
#cp src/local/$dir/$parallelint test/parallel/$dir/$parallelint

done

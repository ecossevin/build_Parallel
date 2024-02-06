#!/bin/bash

set -x
set -e

source ~/venv/bin/activate
which python3

export PATH=/home/gmap/mrpm/cossevine/build_Parallel:$PATH
#export PATH=/home/gmap/mrpm/marguina/fxtran-acdc/bin:$PATH
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

#for f in \
#  arpifs/phys_dmn/apl_arpege_init.F90                                    \
#  arpifs/phys_dmn/apl_arpege_init_surfex.F90                             \
#  arpifs/phys_dmn/apl_arpege_oceanic_fluxes.F90                          \
#  arpifs/phys_dmn/apl_wind_gust.F90                                      \
#  arpifs/phys_dmn/mf_phys_mocon.F90                                      \
#  arpifs/phys_dmn/apl_arpege_shallow_convection_and_turbulence.F90       \
#  arpifs/phys_dmn/apl_arpege_albedo_computation.F90                      \
#  arpifs/phys_dmn/apl_arpege_aerosols_for_radiation.F90                  \
#  arpifs/phys_dmn/apl_arpege_cloudiness.F90                              \
#  arpifs/phys_dmn/apl_arpege_radiation.F90                               \
#  arpifs/phys_dmn/apl_arpege_soil_hydro.F90                              \
#  arpifs/phys_dmn/apl_arpege_deep_convection.F90                         \
#  arpifs/phys_dmn/apl_arpege_surface.F90                                 \
#  arpifs/phys_dmn/apl_arpege_precipitation.F90                           \
#  arpifs/phys_dmn/apl_arpege_hydro_budget.F90                            \
#  arpifs/phys_dmn/apl_arpege_dprecips.F90                                \
#  arpifs/phys_dmn/apl_arpege_atmosphere_update.F90                       \
#  arpifs/adiab/cputqy_aplpar_expl.F90                                    \
#  arpifs/adiab/acctnd0.F90                                               \
#  arpifs/adiab/cputqy0.F90                                               \
#  arpifs/phys_dmn/mf_phys_transfer.F90                                   \
#  arpifs/phys_dmn/apl_arpege_surface_update.F90                          \
#  arpifs/phys_dmn/apl_arpege.F90                                         \
#  arpifs/phys_dmn/mf_phys_prep.F90                                       \
#  arpifs/phys_dmn/mf_phys_init.F90                                       \
#  arpifs/phys_dmn/mf_phys.F90                                            \
#  arpifs/phys_dmn/mf_phys_save_phsurf_part2.F90                          \
#  arpifs/phys_dmn/mf_phys_save_phsurf_part1.F90                          \
#  arpifs/phys_dmn/mf_phys_fpl_part2.F90                                  \
#  arpifs/phys_dmn/mf_phys_fpl_part1.F90                                  \
#  arpifs/phys_dmn/acvppkf.F90
#do
#done

f=arpifs/phys_dmn/apl_arpege.F90
echo "==> $f <=="

# pointerParallel.pl --types-fieldapi-dir types-fieldapi --post-parallel synchost --only-if-newer --version src/local/$f 
dir=$(dirname $f)
echo "DIR = $dir"
echo "RESOLVE = $(resolve $f)"
g=$(resolve $f)
python3 ~/build_Parallel/to_parallel.py --pathpack $p --pathview $g --pathfile $f 
#python3 -m pdb -c continue ~/build_Parallel/to_parallel.py --pathpack $p --pathview $g --pathfile $f 

#to_parallel.py$* src/local/$dir $(resolve $f)
  #pointerParallel.pl $* --use-acpy --types-fieldapi-dir types-fieldapi --post-parallel synchost,nullify --version --dir src/local/$dir $(resolve $f)


#grep _parallel src/local/arpifs/phys_dmn/apl_arpege_parallel.F90

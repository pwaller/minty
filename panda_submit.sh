#! /usr/bin/env bash 

source /afs/cern.ch/atlas/offline/external/GRID/DA/panda-client/latest/etc/panda/panda_setup.sh

BADFILES=$(find . -wholename "*/.git/*" -or -iname "*.eps" -or -iname "*.png" | 
            cut -d'/' -f2- | xargs | sed -r 's/ /,/g')

PASS=5

echo group10.phys-sm.data10_7TeV.period{A..I}.NoGRL.NTUP_PROMPTPHOT.p231/ |
tr ' ' $'\n' | 
xargs -I{} -n1 prun                                                                          \
    --inDS {}                                                                   \
    --outDS user.PeterWaller.purity.paudata.good.period.A.to.I.pass.$PASS/      \
    --noBuild                                                                    \
    --outputs output.root                                                        \
    --nGBPerJob=3                                                                \
    --writeInputToTxt=IN:inputs.txt                                              \
    --excludeFile=input.txt,$BADFILES                                           \
    --extFile=$(ls minty/external/OQMaps/*.root | xargs echo | sed 's/ /,/g') \
    --exec './run_analysis.py analyses.purity PurityAnalysis -Ggrls/official inputs.txt'   \
    --athenaTag=16.0.0                                                           \
    $@ 

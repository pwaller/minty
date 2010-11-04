#! /usr/bin/env bash 

source /afs/cern.ch/atlas/offline/external/GRID/DA/panda-client/latest/etc/panda/panda_setup.sh

BADFILES=$(find . -wholename "*/.git/*" -or -iname "*.eps" -or -iname "*.png" | 
            cut -d'/' -f2- | xargs | sed -r 's/ /,/g')

prun    \
    --inDS group10.phys-sm.data10_7TeV.periodI.NoGRL.NTUP_PROMPTPHOT.p231/      \
    --outDS user.PeterWaller.purity.paudata.periodI.1                           \
    --noBuild                                                                   \
    --outputs output.root                                                       \
    --nFilesPerJob=100                                                          \
    --writeInputToTxt=IN:inputs.txt                                             \
    --excludeFile=input.txt,$BADFILES \
    --extFile=$(ls minty/external/OQMaps/*.root | xargs echo | sed 's/ /,/g') \
    --exec './run_analysis.py analyses.purity PurityAnalysis -Ggrls/official inputs.txt'   \
    --athenaTag=16.0.0                                                          \
    -v $@

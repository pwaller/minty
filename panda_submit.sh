#! /usr/bin/env bash 

source /afs/cern.ch/atlas/offline/external/GRID/DA/panda-client/latest/etc/panda/panda_setup.sh

BADFILES=$(find . -wholename "*/.git/*" -or -iname "*.eps" -or -iname "*.png" | 
            cut -d'/' -f2- | xargs | sed -r 's/ /,/g')

BADFILES=.git,\*.png,\*.eps

PASS=10

echo {A..I} |
tr ' ' $'\n' | 
xargs -I{} -n1 -P8 prun                                                         \
    --inDS group10.phys-sm.data10_7TeV.period{}.NoGRL.NTUP_PROMPTPHOT.p231/      \
    --outDS user.PeterWaller.purity.paudata.good.period.A.to.I.pass.$PASS.period{}/ \
    --noBuild                                                                    \
    --outputs output.root                                                        \
    --nGBPerJob=MAX                                                              \
    --writeInputToTxt=IN:inputs.txt                                              \
    --excludeFile=input.txt,$BADFILES                                           \
    --extFile=$(ls minty/external/OQMaps/*.root | xargs echo | sed 's/ /,/g') \
    --exec './run_analysis.py analyses.purity PurityAnalysis -Ggrls/official inputs.txt' \
    --tmpDir /tmp/pwaller/pass.$PASS.period{}/                                 \
    --excludedSite=ANALY_GRIF-LPNHE \
    --athenaTag=16.0.0                                                           \
    $@ 

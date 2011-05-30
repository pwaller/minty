from minty.utils import deferred_root_loader
import ROOT as R

#c_skimtree = deferred_root_loader("skimtree.cxx+", "skimtree")

def skimtree(destfile, keepevents, input_tree):
    fout = R.TFile(destfile, "recreate")
    fout.cd()
    input_tree.SetBranchStatus("*")
    output_tree = input_tree.CloneTree(0)
    for event in keepevents:
        input_tree.GetEntry(event)
        output_tree.Fill()

    fout.Write()
    fout.Close()
    return True

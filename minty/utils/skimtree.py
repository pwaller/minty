from minty.utils import deferred_root_loader
import ROOT as R

c_skimtree = deferred_root_loader("skimtree.cxx+", "skimtree")

def skimtree(destfile, destname, keepevents, input_tree):
    fout = R.TFile(destfile, "recreate")
    fout.cd()
    input_tree.SetBranchStatus("*")
    output_tree = input_tree.CloneTree(0)
    output_tree.AutoSave()
    keepevents = map(long, keepevents)
    result = c_skimtree(input_tree, output_tree, keepevents)
    
    output_tree.Print()
    fout.Write()
    fout.Close()
    return result

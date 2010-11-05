#! /usr/bin/env python

import ROOT as R
from ROOT import TFile, gROOT, gStyle

import minty
from minty.utils import canvas
import minty.histograms.clever_stack as C
from minty.histograms.manager import expand_hname
from minty.histograms import fixup_hist_units

class NestedTree(dict):
    __slots__ = ("name", "parent")
    
    def __init__(self, name=None, parent=None):
        super(NestedTree, self).__init__()
        self.name = name
        self.parent = parent

    def __setitem__(self, parts, value):
        if len(parts) <= 1 or (len(parts) == 2 and parts[-1] == "corrected"):
            key = "_".join(parts)
            super(NestedTree, self).__setitem__(key, value)
        else:
            subdict = self.setdefault(parts[0], NestedTree(parts[0], self))
            subdict[parts[1:]] = value

    def __getattr__(self, what):
        return self[what]

    @property
    def as_tree(self):
        parts = []
        for key, value in sorted(self.iteritems()):
            if isinstance(value, NestedTree):
                parts.append((key, value.as_tree))
            else:
                parts.append((key, value))
        return parts

def print_tree(leaf, values, depth=0):
    print " "*depth, leaf
    if isinstance(values, (list, tuple)): #hasattr(values, "__iter__"):
        for subleaf, value in values:
            print_tree(subleaf, value, depth+1)
    else:
        print " "*depth, "", values

def normalize_hists(hists, startbin):
    startbin, hibin = hists[0].FindBin(startbin), hists[0].GetNbinsX()
    #value = hists[0].Integral(startbin, hibin)
    for hist in hists:
        hist.Scale(1 / hist.Integral(startbin, hibin))
        
        hist.GetYaxis().SetTitle("Arbitrary Units / [GeV]")
    
def plot_showershape(name, title, variable, *tree_parts, **kwargs):

    fallthrough = kwargs.pop("fallthrough", 0)
    def get_name(tree_part):
        for i in xrange(fallthrough):
            if not tree_part.parent:
                break
            tree_part = tree_part.parent
        return tree_part.name

    with canvas() as c:
        if "logy" in kwargs: c.SetLogy()
        
        namehs = [(get_name(tp), fixup_hist_units(tp[variable])) for tp in tree_parts]
        if "EtCone" in name:
            normalize_hists([h for n, h in namehs], 10)
        hs = [(h, None, hname) for hname, h in namehs]
        sl = C.StackLegend(name, "RT", title, *hs)
        sl.Draw()
        name = "_".join(expand_hname(name, variable))
        c.SaveAs("plots/purity/%s.eps" % name)

def plot_pt(name, tree_part):
    pass

def main():
    f = TFile.Open("analyses/test.root")

    htree = histogram_tree = NestedTree()        
    for key in f.GetListOfKeys():
        histogram_tree[key.GetName().split("_")] = key.ReadObj()
    
    allpt = htree.photon.ptcl.all
    lopt = htree.photon.ptcl.lte40
    hipt = htree.photon.ptcl.gt40
    
    for logy in [True, False]:
        for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected", "Rhad", "DeltaE", "Eratio", "etas2", "fside", "reta", "rphi", "wstot"]:
        
            n = what + ("_logy" if logy else "")
        
            plot_showershape("shower_%s_pt_all" % n, "%s vs tightness" % what, what, 
                             allpt.loose, allpt.nontight, allpt.rtight, logy=logy)
                             
            plot_showershape("shower_%s_pt_lopt" % n, "%s vs tightness (p_{T} < 40GeV)" % what, what,
                             lopt.loose, lopt.nontight, lopt.rtight, logy=logy)
                             
            plot_showershape("shower_%s_pt_hipt" % n, "%s vs tightness (p_{T} > 40GeV)" % what, what,
                             hipt.loose, hipt.nontight, hipt.rtight, logy=logy)
            
            plot_showershape("shower_%s_pt_lovshi_tight" % n, "%s vs p_{T}" % what, what,
                             lopt.rtight, hipt.rtight, fallthrough=1, logy=logy)
                             
            plot_showershape("shower_%s_pt_lovshi_tight_log" % n, "%s vs p_{T}" % what, what,
                             lopt.rtight, hipt.rtight, fallthrough=1, logy=logy)
    #print_tree("root", histogram_tree.as_tree)
    
if __name__ == "__main__":
    gROOT.SetBatch()
    gROOT.SetStyle("Plain")
    gStyle.SetTextFont(22)
    gStyle.SetStatFont(22)
    gStyle.SetTitleFont(22, "")
    gStyle.SetTitleFont(22, "xyz")
    gStyle.SetLabelFont(22, "xyz")
    gStyle.SetLineWidth(1)
    gStyle.SetPalette(1)

    main()

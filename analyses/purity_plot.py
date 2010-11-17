#! /usr/bin/env python

import ROOT as R
from ROOT import TFile, gROOT, gStyle

import minty
from minty.utils import canvas
import minty.histograms.better_stack as C
from minty.histograms.manager import expand_hname
from minty.histograms import fixup_hist_units

# Just a concept
"""
class FellThroughTree(object):
    def __init__(self, parent):
        self.parent = parent

    def keys():
        for key, value in self.parent.iteritems():
    
    def __getattr__(self, what):
        return self[what]
    
    def __getitem__(self, what):
        pass
"""        

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
    
    def get_convert_tkey(self, what):
        if what not in self:
            print "Attribute not found:", self.keys()
        
        value = super(NestedTree, self).__getitem__(what)
        
        if isinstance(value, R.TKey):
            obj = value.ReadObj()
            super(NestedTree, self).__setitem__(what, obj)
            return obj
            
        return value
    
    def __getitem__(self, what):
        try:
            if "_" in what:
                # Resolve underscores
                leaf = self
                parts = what.split("_")
                while parts:
                    part = parts.pop(0)
                    if part not in leaf:
                        raise AttributeError(part)
                    leaf = leaf[part]
                return leaf
        except AttributeError:
            if what not in self:
                raise
            
        return self.get_convert_tkey(what)

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
    
def plot(name, title, variable, *tree_parts, **kwargs):

    fallthrough = kwargs.pop("fallthrough", 0)
    def get_name(tree_part):
        for i in xrange(fallthrough):
            if not tree_part.parent:
                break
            tree_part = tree_part.parent
        return tree_part.name

    logy = kwargs.pop("logy", None)
    normalize = kwargs.pop("normalize", None)
    pos = kwargs.pop("pos", "RT")

    with canvas() as c:
        if logy: c.SetLogy()
        
        namehs = [(get_name(tp), fixup_hist_units(tp[variable])) for tp in tree_parts]
        if normalize is True:
            title += " (normalized)"
            for n, h in namehs:
                h.GetYaxis().SetTitle("Arbitrary Units")
                h.Scale(1. / h.Integral())
        elif normalize:
            try:
                normalize_hists([h for n, h in namehs], normalize)
                title += " (normalized to %s above %i GeV)" % (namehs[0][0], normalize)
            except ZeroDivisionError:
                pass
                
        hs = [(h, None, hname) for hname, h in namehs]
        sl = C.StackLegend(name, pos, title, *hs)
        sl.Draw()
        name = "_".join(expand_hname(name, variable))
        c.SaveAs("plots/purity/%s.eps" % name)

def plot_pt(name, tree_part):
    pass

def make_lots_of_plots(ph):
    
    allpt = ph.ptcl.all
    lopt = ph.ptcl.lte40
    hipt = ph.ptcl.gt40
    vhipt = ph.ptcl.gt100
    
    for logy in [True, False]:
        for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected", 
                     "Rhad", "DeltaE", "Eratio", "etas2", "fside", "reta", 
                     "rphi", "wstot"]:
        
            n = what + ("_logy" if logy else "")
        
            plot("shower_%s_pt_all" % n, "%s vs tightness" % what, what, 
                 allpt.loose, allpt.nontight, allpt.rtight, logy=logy)
                             
            plot("shower_%s_pt_lopt" % n, "%s vs tightness (p_{T} < 40GeV)" % what, what,
                 lopt.loose, lopt.nontight, lopt.rtight, logy=logy)
                             
            plot("shower_%s_pt_hipt" % n, "%s vs tightness (p_{T} > 40GeV)" % what, what,
                 hipt.loose, hipt.nontight, hipt.rtight, logy=logy)
                 
            plot("shower_%s_pt_vhipt" % n, "%s vs tightness (p_{T} > 100GeV)" % what, what,
                 vhipt.loose, vhipt.nontight, vhipt.rtight, logy=logy)
            
            plot("shower_%s_pt_lovshi_tight" % n, "%s vs p_{T}" % what, what,
                 lopt.rtight, hipt.rtight, fallthrough=1, logy=logy)
                             
            plot("shower_%s_pt_lovshi_tight_log" % n, "%s vs p_{T}" % what, what,
                  lopt.rtight, hipt.rtight, fallthrough=1, logy=logy)

def study_trigger_hump():
    pass

def setup_style():

    gROOT.SetBatch()
    gROOT.SetStyle("Plain")
    gStyle.SetTextFont(22)
    gStyle.SetStatFont(22)
    gStyle.SetTitleFont(22, "")
    gStyle.SetTitleFont(22, "xyz")
    gStyle.SetLabelFont(22, "xyz")
    gStyle.SetLineWidth(1)
    gStyle.SetPalette(1)

def plot_trigger_object_counts(ht):
    
    objcounts = ht.g10_loose, ht.g20_loose, ht.g30_loose, ht.g40_loose
    objcounts = [htpart.obj for htpart in objcounts]
    print objcounts[0].count
    objcounts[0].count.GetXaxis().SetTitle("Number of photons causing trigger")
    
    plot("trig_objcounts", "Trigger object counts", "count",
         fallthrough=2, logy=True, *objcounts)

def showershapes(ht):

    #positioning = dict(
        #Et
    positioning = dict(
        Eratio="RB",
        etas2="CB",
        reta="CB",
        rphi="LT",
        wstot="LB",
    )   
    
    ptall = ht.ptcl_all
    for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected", 
                 "Rhad", "Rhad1", "DeltaE", "Eratio", "etas2", "fside", "reta", 
                 "rphi", "wstot", "ws3", "et"]:
        
        plot("shower_vstight", "%s vs tightness" % what, what, 
             ptall.loose, ptall.nontight, ptall.rtight, logy=False, 
             pos=positioning.get(what, "RT"), normalize=True)
             
    for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected"]:
        plot("shower_etconeshape", "%s vs tightness" % what, what, 
             ptall.loose, ptall.nontight, ptall.rtight, logy=False, normalize=5,
             pos=positioning.get(what, "RT"))
             
    for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected"]:
        plot("shower_etconeshape_norm10", "%s vs tightness" % what, what, 
             ptall.loose, ptall.nontight, ptall.rtight, logy=False, normalize=10,
             pos=positioning.get(what, "RT"))

    for what in ["EtCone20", "EtCone30", "EtCone40", "EtCone40_corrected", 
                 "Rhad", "Rhad1", "DeltaE", "Eratio", "etas2", "fside", "reta", 
                 "rphi", "wstot", "ws3", "et"]:
        plot("shower_tight_vspt", "%s vs pt" % what, what, 
             ht.ptcl_lte40.rtight, ht.ptcl_gt40.rtight, logy=False, 
             pos=positioning.get(what, "RT"), fallthrough=1, normalize=10)

def main(argv):
    setup_style()
    print "Here.."
    
    import re
    multiunderscore = re.compile("[_]{2,}")
    
    f = TFile.Open(argv[0])

    ht = histogram_tree = NestedTree()
    names = []
    for key in f.GetListOfKeys():
        name = multiunderscore.sub("_", key.GetName().strip("_"))
        names.append(name)
        histogram_tree[name.split("_")] = key #.ReadObj()
    
    with open("all_names.txt", "w") as fd:
        fd.write("\n".join(names))
    
    plot_trigger_object_counts(ht)
    showershapes(ht.photon)
    
    #ph = htree.photontrig.g20.loose
    #make_lots_of_plots(ph)
    
    
if __name__ == "__main__":

    from sys import argv
    main(argv[1:])

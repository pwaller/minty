#! /usr/bin/env python

# https://twiki.cern.ch/twiki/bin/view/AtlasProtected/PhotonCrossSection2010

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from minty import main, AnalysisBase
from minty.histograms import double_bins, mirror_bins

from math import cosh

class ExtraEgammaInfo(object):
    """
    Give egammas some additional properties so that one can write, e.g.
    good_photons = [ph for ph in event.photons if ph.fiducial]
    """
    @property
    def good_eta(self):
        return abs(self.etas2) < 1.37 or 1.52 <= abs(self.etas2) < 2.37
        
    @property
    def fiducial(self):
        return self.cl.pt >= 15000 and self.good_eta

def counts(ana, event, name, objects):
    """
    Fill a sparse histogram for counting cuts (allows one
    """
           
    pv = any(v.nTracks >= 3 for v in event.vertices)
        
    ev_cuts = event.is_grl, pv, event.EF.g10_loose
    
    cuts = "loose:tight:robust_tight:fiducial:oq:grl:pv:g10_loose"
    cut_binning = ((2, 0, 2),) * len(cuts.split(":"))
    fill_counts = ana.h.get(name, "counts", b=cut_binning, 
                            title="%s counts passing cuts:%s" % (name, cuts))
    
    for o in objects:
        fill_counts(o.loose, o.tight, o.robust_tight, o.pass_fiducial, o.good_oq, 
                    *ev_cuts)

def plot_pts(ana, name, bins, obj):
    """
    Plot Pt histograms
    """
    ana.h.get(name, "pt",    b=(bins,))(obj.pt)
    ana.h.get(name, "pt_cl", b=(bins,))(obj.cl.pt)
    
    ana.h.get(name, "pt_smearmat",    b=(bins, bins))(obj.truth.pt, obj.pt)
    ana.h.get(name, "pt_cl_smearmat", b=(bins, bins))(obj.truth.pt, obj.cl.pt)
    
    return
    if ana.have_truth:
        ana.h.get(name, "pt_true", b=(bins,))(obj.truth.pt)
        
        if type(obj).__name__ == "Photon":
            pt_res    = obj.truth.pt - obj.pt
            pt_cl_res = obj.truth.pt - obj.cl.pt
        elif type(obj).__name__ == "Electron":
            name += ("reciprocal",)
            pt_res    = 1/obj.truth.pt - 1/obj.pt
            pt_cl_res = 1/obj.truth.pt - 1/obj.cl.pt
        else:
            raise RuntimeError("Unexpected object type")
        
        ana.h.get(name, "pt_res",    b=(ana.ptres_binning,))(pt_res)
        ana.h.get(name, "pt_cl_res", b=(ana.ptres_binning,))(pt_cl_res)         

def plot_object(ana, event, name, obj):
    """
    Plot histograms for one object (electron, photon)
    """
    
    plot_pts(ana, name,           ana.ptbins,      obj)
    
    # Once with finer binning
    plot_pts(ana, (name, "fine"), ana.ptbins_fine, obj)
    
    # More sets of plots come later

def plots(ana, event):
    """
    Make plots for the event
    """
    # Could do a loop over [("electron", ph.electrons), ("photon", ph.photons)]
    # but left it expanded as two loops just to get an idea what it looks like
    
    for ph in event.photons:
        if not (ph.tight and ph.pass_fiducial): continue
        plot_object(ana, event, ("photon", "fiducial"), ph)
        
    for el in event.electrons:
        if not (el.tight and el.pass_fiducial): continue
        plot_object(ana, event, ("electron", "fiducial"), el)

def make_tight_ph_tree(ana, event):
    """
    An example of cloning part of a tree (only tight photons and "Global", which
    are 
    """
    from minty.treedefs import Photon, Global
    new_tree = ana.tree_manager.get("mytree", outfile="tight_phtree.root", 
        new=[Photon], cloned=(event, [Global]))

    # Copy tight photons to the new tree
    for ph in [p for p in event.photons if p.tight]:
        new_tree.photon.new(ph)
        
    new_tree.Fill()

class DirectPhotonAnalysis(AnalysisBase):
    def __init__(self, tree, options):
    
        """
        # Additional information to decorate default objects with
        from minty.treedefs import Photon, Electron
        self.tree_extras = {
            Photon   : ExtraEgammaInfo,
            Electron : ExtraEgammaInfo,
        }
        """
    
        super(DirectPhotonAnalysis, self).__init__(tree, options)
        
        self.ptbins = ("var", 15, 20, 25, 30, 35, 40, 50, 60, 100)
        self.etabins = mirror_bins(("var", 0., 0.60, 1.37, 1.52, 1.81, 2.37))
        
        self.ptbins_fine  = double_bins(self.ptbins)
        self.etabins_fine = double_bins(self.etabins)
        
        # Binning for resolution plots
        self.res_binning = 1000, -10, 10
        
        from minty.utils import mark_is_grl, mark_object_quality
        # Tasks to run in order
        self.tasks.extend([
            mark_is_grl,
            mark_object_quality,
            lambda a, e: counts(a, e, "photons", e.photons),
            plots,
            #make_tight_ph_tree,
        ])

def do_more_stuff(ana, event):
    pass

class DirectPhotonAnalysisExtension(DirectPhotonAnalysis):
    """
    Doing more stuff as well as the basic analysis
    """
    def __init__(self, tree, options):
        super(DirectPhotonAnalysisExtension, self).__init__(tree, options)
        
        self.tasks.extend([
            do_more_stuff,
        ])

if __name__ == "__main__":
    main(DirectPhotonAnalysis)
    
    

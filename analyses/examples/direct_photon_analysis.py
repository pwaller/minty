#! /usr/bin/env python

# https://twiki.cern.ch/twiki/bin/view/AtlasProtected/PhotonCrossSection2010

# Scripts expect to be run with a cwd where "minty" and "pytuple" are present.
# (Or minty and pytuple are in the path)
import os; import sys; sys.path.insert(0, os.getcwd())

from minty import main, AnalysisBase
from minty.histograms import double_bins, mirror_bins, scale_bins
from minty.treedefs.egamma import Photon, Electron

from math import cosh

def counts(ana, event, name, objects):
    """
    Fill a sparse histogram for counting cuts (allows one
    """
           
    pv = any(v.nTracks >= 3 for v in event.vertices)
        
    ev_cuts = event.is_grl, pv, event.EF.g10_loose
    
    cuts = "loose;tight;robust_tight;fiducial;oq;grl;pv;g10_loose"
    cut_binning = ((2, 0, 2),) * len(cuts.split(";"))
    fill_counts = ana.h.get(name, "counts", b=cut_binning, 
                            title="%s counts passing cuts;%s;" % (name, cuts))
    
    for o in objects:
        fill_counts(o.loose, o.tight, o.robust_tight, o.pass_fiducial, o.good_oq, 
                    *ev_cuts)

TITLE_SMEAR = "p_{T} smearing matrix;Truth p_{T} [MeV];Measured p_{T} [MeV]"
TITLE_SMEAR_CLUS = "p_{T} smearing matrix;Truth p_{T} [MeV];Measured (cluster) p_{T} [MeV]"

def plot_pts(ana, name, bins, obj):
    """
    Plot Pt histograms
    """
    def T(what=""): return "%sp_{T};%sp_{T} [MeV];N events" % (what, what)
    
    ana.h.get(name, "pt",    b=(bins,), title=T()          )(obj.pt)
    ana.h.get(name, "pt_cl", b=(bins,), title=T("cluster "))(obj.cl.pt)
    
    ana.h.get(name, "pt_vs_eta",    b=(bins, ana.etabins), title="cluster p_{T} vs #eta;cluster p_{T} [MeV];#eta_{S2};")(obj.cl.pt, obj.etas2)
    
    if ana.info.have_truth and obj.truth.matched:
    
        ana.h.get(name, "match_count", b=((2, 0, 2),))(obj.truth.matched)
    
        ana.h.get(name, "pt_smearmat",    b=(bins, bins), title=TITLE_SMEAR     )(obj.truth.pt, obj.pt)
        ana.h.get(name, "pt_cl_smearmat", b=(bins, bins), title=TITLE_SMEAR_CLUS)(obj.truth.pt, obj.cl.pt)
    
        ana.h.get(name, "pt_true", b=(bins,), title=T("true "))(obj.truth.pt)
        ana.h.get(name, "true_pt_vs_eta",    b=(bins, ana.etabins), title="true p_{T} vs #eta;true p_{T} [MeV];true #eta_{S2};")(obj.truth.pt, obj.truth.eta)
        
        if isinstance(obj, Photon):
            def T(what=""): return "Photon %sp_{T};%s#Deltap_{T} [MeV];N events" % (what, what)
            ptres_binning = 1000, -20000, 20000
            pt_res    = obj.truth.pt - obj.pt
            pt_cl_res = obj.truth.pt - obj.cl.pt
            
        elif isinstance(obj, Electron):
            def T(what=""): return "Electron %sp_{T};%s#Deltap_{T} [1/MeV];N events" % (what, what)
            ptres_binning = 1000, -10, 10
            name += ("reciprocal",)
            pt_res    = 1/obj.truth.pt - 1/obj.pt
            pt_cl_res = 1/obj.truth.pt - 1/obj.cl.pt
            
        else:
            raise RuntimeError("Unexpected object type")
        
        ana.h.get(name, "pt_res",    b=(ptres_binning,), title=T()         )(pt_res)
        ana.h.get(name, "pt_cl_res", b=(ptres_binning,), title=T("cluster "))(pt_cl_res)

def plot_object(ana, event, name, obj):
    """
    Plot histograms for one object (electron, photon)
    """
    
    plot_pts(ana, ("eta_all", name), ana.ptbins,      obj)
    plot_pts(ana, ("fine",    name), ana.ptbins_fine, obj)
    
    # Make pt plots in bins of eta
    for i, (elow, ehi) in enumerate(zip(ana.etabins_sym[1:], ana.etabins_sym[2:])):
        if elow <= obj.etas2 < ehi:
            plot_pts(ana, ("eta_%i" % i, name), ana.ptbins, obj)

    plot_pts(ana, ("auth_%i" % obj.author,    name), ana.ptbins_fine, obj)#
    
def plots(ana, event):
    """
    Make plots for the event
    """
    # Could do a loop over [("electron", ph.electrons), ("photon", ph.photons)]
    # but left it expanded as two loops just to get an idea what it looks like
    
    pv = any(v.nTracks >= 3 for v in event.vertices)
    
    if not all((pv, event.is_grl, event.EF.g10_loose)):
        return
        
    for ph in event.photons:
        if not (ph.pass_fiducial and ph.loose and ph.good_oq): continue
        if ana.obj_selection and not ana.obj_selection(ph):
            continue
        
        plot_object(ana, event, ("photon", "loose"), ph)
        if not ph.robust_tight: continue
        plot_object(ana, event, ("photon", "rtight"), ph)

class DirectPhotonAnalysis(AnalysisBase):
    def __init__(self, tree, options):
    
        super(DirectPhotonAnalysis, self).__init__(tree, options)
        
        self.ptbins = ("var", 15, 20, 25, 30, 35, 40, 50, 60, 100, 110)
        self.ptbins = scale_bins(self.ptbins, 1000)
        self.etabins_sym = "var", 0., 0.60, 1.37, 1.52, 1.81, 2.37
        self.etabins = mirror_bins(self.etabins_sym)
        
        self.ptbins_fine  = double_bins(self.ptbins,  4)
        self.etabins_fine = double_bins(self.etabins, 4)
        
        # Tasks to run in order
        self.tasks.extend([
            lambda a, e: counts(a, e, "photon", e.photons),
            plots,
        ])
        
        if self.options.obj_selection:
            expr = "lambda o: %s" % self.options.obj_selection
            args = expr, "<options.obj_selection>", "eval"
            self.obj_selection = eval(compile(*args))
        else:
            self.obj_selection = None
        
    def finalize(self):
        super(DirectPhotonAnalysis, self).finalize()

if __name__ == "__main__":
    main(DirectPhotonAnalysis)
    
    

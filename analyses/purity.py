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
    return
    def T(what=""): return "%sp_{T};%sp_{T} [MeV];N events" % (what, what)
    
    hget = ana.h.get
    
    hget(name, "pt",    b=(bins,), title=T()          )(obj.pt)
    hget(name, "pt_cl", b=(bins,), title=T("cluster "))(obj.cl.pt)
    
    hget(name, "pt_vs_eta",    b=(bins, ana.etabins), title="cluster p_{T} vs #eta;cluster p_{T} [MeV];#eta_{S2};")(obj.cl.pt, obj.etas2)
    
    if ana.info.have_truth and obj.truth.matched:
    
        hget(name, "match_count", b=((2, 0, 2),))(obj.truth.matched)
    
        hget(name, "pt_smearmat",    b=(bins, bins), title=TITLE_SMEAR     )(obj.truth.pt, obj.pt)
        hget(name, "pt_cl_smearmat", b=(bins, bins), title=TITLE_SMEAR_CLUS)(obj.truth.pt, obj.cl.pt)
    
        hget(name, "pt_true", b=(bins,), title=T("true "))(obj.truth.pt)
        hget(name, "true_pt_vs_eta",    b=(bins, ana.etabins), title="true p_{T} vs #eta;true p_{T} [MeV];true #eta_{S2};")(obj.truth.pt, obj.truth.eta)
        
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
        
        hget(name, "pt_res",    b=(ptres_binning,), title=T()         )(pt_res)
        hget(name, "pt_cl_res", b=(ptres_binning,), title=T("cluster "))(pt_cl_res)

def plot_isolation(ana, name, obj):
    hget = ana.h.get
    
    hget(name, "et",        b=[ana.ptbins]   )(obj.et)
    hget(name, "etas2",     b=[ana.etabins]  )(obj.etas2)
    hget(name, "Rhad",      b=[(100, -2, 2)] )(obj.Rhad)
    hget(name, "Rhad1",     b=[(100, -2, 2)] )(obj.Rhad1)
    
    hget(name, "reta",      b=[(20, 0.9, 1)] )(obj.reta)
    hget(name, "rphi",      b=[(15, 0.8, 1)] )(obj.rphi)
    
    hget(name, "Eratio",    b=[(15, 0.7, 1)] )(obj.Eratio)
    hget(name, "DeltaE",    b=[(15, 0, 500)] )(obj.deltaE)
    
    hget(name, "wstot",     b=[(15, 0, 5)]   )(obj.wstot)
    hget(name, "ws3",       b=[(15, 0, 5)]   )(obj.ws3)
    hget(name, "fside",     b=[(20, 0, 1.25)])(obj.fside)
    
    hget(name, "EtCone20",  b=[(100, -5000, 50000)])(obj.EtCone20)
    hget(name, "EtCone30",  b=[(100, -5000, 50000)])(obj.EtCone30)
    hget(name, "EtCone40",  b=[(100, -5000, 50000)])(obj.EtCone40)
    
    hget(name, "EtCone20_corrected",  b=[(100, -5000, 50000)])(obj.EtCone20_corrected)
    hget(name, "EtCone30_corrected",  b=[(100, -5000, 50000)])(obj.EtCone30_corrected)
    hget(name, "EtCone40_corrected",  b=[(100, -5000, 50000)])(obj.EtCone40_corrected)


def plot_object(ana, name, obj):
    """
    Plot histograms for one object (electron, photon)
    """
    
    plot_pts(ana, (name, "eta_all"), ana.ptbins,      obj)
    plot_pts(ana, (name, "fine"),    ana.ptbins_fine, obj)
    
    plot_isolation(ana, name, obj)
    
    # Make pt plots in bins of eta
    for i, (elow, ehi) in enumerate(zip(ana.etabins_sym[1:], ana.etabins_sym[2:])):
        if not elow <= obj.etas2 < ehi:
            continue
        name_eta = (name, "eta_%i" % i)
        plot_pts(ana, name_eta, ana.ptbins, obj)
        plot_isolation(ana, name_eta, obj)

    name_auth = (name, "auth_%i" % obj.author)
    plot_pts(ana, name_auth, ana.ptbins_fine, obj)
    plot_isolation(ana, name_auth, obj)
    
def plot_objects_multi_cuts(ana, name, obj):

    plot_object(ana, (name, "loose"), obj)
    if obj.robust_tight:
        assert obj.robust_nontight, "Found a tight object which isn't nontight!"
        
    if not obj.robust_nontight: return
    plot_object(ana, (name, "nontight"), obj)
    
    if not obj.robust_tight: return
    plot_object(ana, (name, "rtight"), obj)

def plot_objects_multi_pt(ana, name, obj):
    plot_objects_multi_cuts(ana, (name, "ptcl_all"), obj)
    
    if obj.cl.pt > 40000:
        plot_objects_multi_cuts(ana, (name, "ptcl_gt40"), obj)
    else:
        plot_objects_multi_cuts(ana, (name, "ptcl_lte40"), obj)

def plots(ana, event):
    """
    Make plots for the event
    """
    # Could do a loop over [("electron", ph.electrons), ("photon", ph.photons)]
    # but left it expanded as two loops just to get an idea what it looks like
    
    pv = any(v.nTracks >= 3 for v in event.vertices)
    
    #if not all((pv, event.is_grl, event.EF.g10_loose)): return
        
    for ph in event.photons:
    
        #assert ph.robust_tight_test == ph.robust_tight
    
        if not (ph.pass_fiducial and ph.loose and ph.good_oq): continue
        if ana.obj_selection and not ana.obj_selection(ph):
            continue
        
        plot_objects_multi_pt(ana, "photon", ph)

class PurityAnalysis(AnalysisBase):
    def __init__(self, tree, options):
    
        super(PurityAnalysis, self).__init__(tree, options)
        
        self.ptbins = ("var", 15, 20, 25, 30, 35, 40, 50, 60, 100, 140, 180, 
                       220, 300, 380, 460, 620, 1000)
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
        super(PurityAnalysis, self).finalize()

if __name__ == "__main__":
    main(PurityAnalysis)
    
    

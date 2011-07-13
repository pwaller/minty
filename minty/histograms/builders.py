import ROOT as R

def build_histogram_auto(name, title, binning):
    """
    Automatically create a TH{1,2,3} or THnSparse as appropriate
    """

    dimensions = len(binning)
    
    if dimensions <= 3:
        return build_histogram_plain(name, title, binning)
    else:
        return build_histogram_sparse(name, title, binning)

def build_histogram_plain(name, title, binning):
    """
    Build a histogram inheriting the TH1.
    
    `binning` should be a list of tuples, describing the bins for each axis.
    """
    dimensions = len(binning)
    TH = {1: R.TH1D, 2: R.TH2D, 3: R.TH3D}[dimensions]
    binning_args, fixup_axes = [], []
    
    class VariableBins(list): pass
    class NamedBins(list): pass
    
    AXES_GETTERS = [R.TH1.GetXaxis, R.TH1.GetYaxis, R.TH1.GetZaxis]
    for bins, axis_getter in zip(binning, AXES_GETTERS):
        if len(bins) == 3:
            binning_args.extend(bins)
        elif bins[0] == "var":
            variable_bins = bins[1:]
            dummy_bins = (len(variable_bins), 
                          variable_bins[0], 
                          variable_bins[-1])
            binning_args.extend(dummy_bins)
            fixup_axes.append((axis_getter, VariableBins(variable_bins)))
            
        elif bins[0] == "named" and all(isinstance(b, basestring) for b in bins):
            bins = bins[1:]
            binning_args = len(bins), 0, len(bins)
            fixup_axes.append((axis_getter, NamedBins(bins)))
            
        else:
            raise RuntimeError("A given set of bins should either be "
                "three long, or the first element must be 'var' to "
                "indicate variable binning")
    
    hname = name.split("/")[-1] # remove path from name
    hist = TH(hname, title, *binning_args)
    hist.Sumw2()
    for fixup_axis, binning in fixup_axes:
        if isinstance(binning, VariableBins):
            fixup_axis(hist).Set(len(binning)-1, array("d", binning))
            
        elif isinstance(binning, NamedBins):
            for i, bin_name in enumerate(binning):
                fixup_axis(hist).SetBinLabel(i+1, bin_name)
        else:
            raise NotImplementedError
        
    filler = hist.Fill
    return hist, filler

def make_sparse_hist_filler(hist):
    dimensions = hist.GetNdimensions()
    def filler(*args, **kwargs):
        w = kwargs.pop("w", 1)
        assert len(args) == dimensions, "Filling THnSparse with wrong number of arguments (%i instead of %i)" % (len(args), dimensions)
        hist.Fill(array('d', args), w)
    return filler

def build_histogram_sparse(name, title, binning):
    """
    Build a THnSparse
    """
    dimensions = len(binning)
    nbins, xmins, xmaxs = array("i", []), array("d", []), array("d", [])
    fixup_axes = []
    
    for i, bins in enumerate(binning):
        if len(bins) == 3:
            nbins.append(bins[0])
            xmins.append(bins[1])
            xmaxs.append(bins[2])
            
        elif bins[0] == "var":
            variable_bins = bins[1:]
            nbins.append(len(variable_bins))
            xmins.append(variable_bins[0])
            xmaxs.append(variable_bins[-1])
            fixup_axes.append((i, variable_bins))
        else:
            raise RuntimeError("A given set of bins should either be "
                "three long, or the first element must be 'var'")

    hname = name.split("/")[-1] # remove path from name
    hist = R.THnSparseD(hname, title, dimensions, 
                        nbins, xmins, xmaxs)
    hist.Sumw2()

    # manual name setting necessary for v15 root
    for d, n in zip(range(dimensions), title.split(";")[1:]):
        hist.GetAxis(d).SetName(n)
        hist.GetAxis(d).SetTitle(n)
                        
    for i, binning in fixup_axes:
        hist.GetAxis(i).Set(len(binning)-1, array("d", binning))
    
    filler = make_sparse_hist_filler(hist)
    return hist, filler

from __future__ import division

import ROOT as R

from ROOT import kWhite, kBlack, kRed, kGreen, kBlue, kYellow, kMagenta, kCyan, kOrange

from ROOT import (kDot, kPlus, kStar, kCircle, kMultiply, kFullDotSmall, 
                  kFullDotMedium, kFullDotLarge, kFullCircle, kFullSquare, 
                  kFullTriangleUp, kFullTriangleDown, kOpenCircle, kOpenSquare, 
                  kOpenTriangleUp, kOpenDiamond, kOpenCross, kFullStar, 
                  kOpenStar)

def MakeStack(name, title, *args):
    h = R.THStack(name, title)
    for arg in args:
        if isinstance(arg, tuple):
            arg, color = arg
            arg.SetLineColor(color)
            arg.SetMarkerColor(color)
        elif not isinstance(arg, (R.TH1, R.TGraph)):
            raise RuntimeError("Arguments should be histograms!")
            
        if isinstance(arg, (R.TGraph, R.TSpline)):
            # Skip graphs. They aren't liked in stacks.
            continue
        
        #with PreserveOwnership(arg):
        h.Add(arg)
    return h
    
def MakeLegend(pos, *items):
    
    #~ if len(titles) < len(items):
        #~ titles += ("",)*(len(items)-len(titles))
    
    h = "LCR"
    v = "BMT"
    if len(pos) != 2: raise RuntimeError("Bad position string, should be 2 chars")
    try:
        h = h.index(pos[0])
        v = v.index(pos[1])
    except KeyError, ValueError:
        raise RuntimeError("Bad position string")
        
    z = 9*3
    x1 = h*(1/3) + (1/z/2)
    x2 = (h+1)*(1/3) - (1/z/2)
    y1 = v*(1/3) + (1/z)
    y2 = (v+1)*(1/3) - (1/z)
    
    x1 = (x1*0.8)+0.1
    y1 = (y1*0.8)+0.1
    x2 = (x2*0.8)+0.1
    y2 = (y2*0.8)+0.1
    
    l = R.TLegend(x1, y1, x2, y2)
    l.SetFillColor(R.kWhite)
    l.SetLineColor(R.kWhite)
    l.SetTextFont(R.gStyle.GetTextFont() // 10 * 10 + 3)
    l.SetTextSize(20)
    
    for item, titles in items:
        if not hasattr(item, "pyNoLegend"):
            l.AddEntry(item, titles)
        
    return l

class StackLegend(object):
    def __init__(self, name, legpos, title, *args, **kwargs):
        #~ hists, colors, titles = zip(*args)
        hists, colors, titles = [], [], []
        for arg in args:
            if isinstance(arg, (R.TH1, R.TGraph, R.TSpline)):
                hists.append(arg)
                colors.append(arg.GetLineColor())
                titles.append(arg.GetTitle())
            elif isinstance(arg, tuple) and len(arg) == 3:
                hists.append(arg[0])
                colors.append(arg[1])
                titles.append(arg[2])
            else:
                raise NotImplementedError
           
        prevColor = None
        hadPrevColor = False
        allSame = True
        for color in colors:
            if prevColor is None and not hadPrevColor:
                prevColor = color
                hadPrevColor = True
            else:
                if color != prevColor:
                    allSame = False
                    break
        
        if allSame:
            colors = [kRed, kBlue, kGreen, kOrange, kMagenta, kCyan]
        
#        print hists
#        print titles
#        print
        
        s = MakeStack(name, title, *zip(hists, colors))
        l = MakeLegend(legpos, *zip(hists, titles))
        
        #with MakeInvisibleCanvas():
        if True:
            s.Draw("nostack")
            
            xTitle = kwargs.get("xTitle", hists[0].GetXaxis().GetTitle())
            yTitle = kwargs.get("yTitle", hists[0].GetYaxis().GetTitle())
            s.GetXaxis().SetTitle(xTitle)
            s.GetYaxis().SetTitle(yTitle)
        
        self.name = name
        self.stack = s
        self.legend = l
        self.args = args
        self.hists = hists
        self.titles = titles
        self.colors = colors
        
    def Draw(self, options = "", graphOptions = "Pz"):
        if "stack" not in options:
            options += " nostack"
        self.stack.Draw(options)
        # Draw any graph objects on top
        for graph, color, title in zip(self.hists, self.colors, self.titles):
            if isinstance(graph, R.TH1):
                continue
            elif isinstance(graph, R.TGraph):
                graph.Draw(graphOptions)
            elif hasattr(graph, "Draw") and callable(graph.Draw):
                graph.Draw("same")
                
        self.legend.Draw()
        return self
        
    def __call__(self, *args, **kwargs): 
        return self.Draw(*args, **kwargs)
        
    def __repr__(self):
        return "<StackLegend name='%s' nHists=%i>" % (self.name, len(self.hists))
    
    def set_x_range(self, x_range):
        lo, hi = x_range
        self.X.SetRange(self.X.FindBin(lo), self.X.FindBin(hi))
    
    @property
    def X(self): return self.stack.GetXaxis()
    @property
    def Y(self): return self.stack.GetYaxis()
    @property
    def H(self): return self.stack.GetHistogram()

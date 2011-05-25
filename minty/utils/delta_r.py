
from math import pi, hypot
pix2 = 2*pi
    
def delta_r(o1, o2):
    """
    Evaluate Delta R between two objects
    """
    d_phi = o1.phi - o2.phi
    if d_phi < -pi: d_phi += pix2
    if d_phi >  pi: d_phi -= pix2
    return hypot(o1.eta - o2.eta, d_phi)

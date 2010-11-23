#! /usr/bin/env python

import virtualenv, textwrap

packages = "minty OQMaps PhotonIDTool pytuple".split()

output = virtualenv.create_bootstrap_script(textwrap.dedent("""
    import os, subprocess
    _install_my_packages = False
    def after_install(options, home_dir):
        if _install_my_packages:
            subprocess.call([join(home_dir, 'bin', 'pip'), 'install', {packages}, '-epwa'])
    
    def adjust_options(options, args):
        if "inst" in args:
            global _install_my_packages
            _install_my_packages = True
        args[:] = ["env"]
""".format(packages=", ".join("'-erepos/%s'" % p for p in packages))))

f = open('ana_bootstrap.py', 'w').write(output)

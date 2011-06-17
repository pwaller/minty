from setuptools import setup, find_packages

setup(
    name="minty",
    packages=find_packages(),
    package_data={'': ["*.yaml"]},
    entry_points={
        "console_scripts" : [
            "minty-py-rep = minty.tools.repeat:main",
            "minty-show-ttree = minty.tools.show_ttree:main",
            "minty-ip-tfile = minty.tools.ipython_file:main",
            "minty-rescale = minty.tools.minty_rescale:main",
            "minty-xs = minty.tools.minty_xsection:main",
            "minty-runperiod-mapping = minty.metadata.period:main",
            "minty-slim = minty.tools.tree.slimmer:main",
        ]
    },
)

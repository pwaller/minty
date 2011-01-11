from setuptools import setup, find_packages

setup(
    name="minty",
    packages=find_packages(),
    entry_points={
        "console_scripts" : [
            "py_rep = minty.tools.repeat:main",
            "show_ttree = minty.tools.show_ttree:main",
            "ip_tfile = minty.tools.ipython_file:main",
            "hmerge = minty.tools.bettermerge:main",
            "minty-rescale = minty.tools.minty_rescale:main",
        ]
    },
    scripts=["scripts/ds_number_to_what"],
)

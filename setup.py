from setuptools import setup, find_packages

setup(
    name="minty",
    packages=find_packages(),
    install_requires=[
        "beaker>=1.5.4"
    ],
    entry_points={
        "console_scripts" : [
            "py_rep = minty.tools.repeat:main",
        ]
    }
)

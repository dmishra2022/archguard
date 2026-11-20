"""Bundles the repository's spec catalog when building from a checkout (pip install ./python/archguard-py,
or a git URL). Builds from an sdist already contain src/archguard/spec."""
import runpy
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

HERE = Path(__file__).resolve().parent


def bundle_spec():
    if (HERE.parent.parent / 'spec' / 'index.yml').is_file():
        runpy.run_path(str(HERE / 'scripts' / 'copy_spec.py'))


class BuildPy(build_py):
    def run(self):
        bundle_spec()
        super().run()


class Sdist(sdist):
    def run(self):
        bundle_spec()
        super().run()


setup(cmdclass={'build_py': BuildPy, 'sdist': Sdist})

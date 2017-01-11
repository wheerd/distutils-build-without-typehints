import os.path
import sys
from distutils.command.build_py import build_py as _build_py
from distutils.core import Command

from strip_type_hints import StripTypeHintsRefactoringTool


class build_without_typehints(Command):

    description = 'build without typehints'

    user_options = []

    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if sys.version_info < (3, 6):
            self.distribution.cmdclass['build_py'] = build_py
            self.reinitialize_command('build_py')
        self.run_command('build')

class build_py(_build_py):
    def initialize_options(self):
        super().initialize_options()
        self.refactoring_tool = StripTypeHintsRefactoringTool()

    def build_module(self, module, module_file, package):
        if not super().build_module(module, module_file, package):
            return False
        if isinstance(package, str):
            package = package.split('.')
        outfile = self.get_module_outfile(self.build_lib, package, module)
        self.refactoring_tool.refactor_file(outfile, write=True)

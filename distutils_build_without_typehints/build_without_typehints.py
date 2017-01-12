import sys
from distutils.command.build_py import build_py as _build_py
from distutils.command.build import build as _build

from .strip_type_hints import StripTypeHintsRefactoringTool


class build_without_typehints(_build):
    description = 'build without typehints'

    def run(self):
        if sys.version_info < (3, 5, 3):
            self.distribution.cmdclass['build_py'] = build_py
            self.reinitialize_command('build_py')
        else:
            cmd = self.reinitialize_command('build_py')
            cmd.set_undefined_options('build_without_typehints',
                                      ('build_lib', 'build_lib'),
                                      ('force', 'force'))
        _build.run(self)

class build_py(_build_py):
    def initialize_options(self):
        _build_py.initialize_options(self)
        self.refactoring_tool = StripTypeHintsRefactoringTool()

    def finalize_options(self):
        self.set_undefined_options('build_without_typehints',
                                   ('build_lib', 'build_lib'),
                                   ('force', 'force'))
        _build_py.finalize_options(self)

    def build_module(self, module, module_file, package):
        if not _build_py.build_module(self, module, module_file, package):
            return False
        if isinstance(package, str):
            package = package.split('.')
        outfile = self.get_module_outfile(self.build_lib, package, module)
        self.refactoring_tool.refactor_file(outfile, write=True)

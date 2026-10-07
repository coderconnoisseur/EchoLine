# PyInstaller entry point: the package's own __main__ uses relative imports.
import sys

from echoline.__main__ import main

sys.exit(main())

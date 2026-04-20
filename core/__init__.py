__version__ = "1.0.0"

from .scanner import scanner
from . import rules
from . import classifier
from . import file_ops
from . import custom_rules
from . import personal_dirs
from . import progress_manager
from . import smart_recognizer
from . import logger
from . import utils
from . import file_classifier

__all__ = [
    "scanner",
    "rules",
    "classifier",
    "file_ops",
    "custom_rules",
    "personal_dirs",
    "progress_manager",
    "smart_recognizer",
    "logger",
    "utils",
    "file_classifier",
]

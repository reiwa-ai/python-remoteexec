__version__ = '0.1.2'
__all__ = ['SnippetRunner',
           'SnippetRunnerLocal',
           'RunningConditions',
           'SnippetLoopHook',
           'SnippetStepHook',
           'SnippetStepErrorHook',
           'COMMON_BUILTINS',
           'COMMON_MODULES',
           'ConflictSolvePolicy',
           'StepErrorApproach',
           ]
from .remoteexec import *
from .communicate import ConflictSolvePolicy
from .hooks import StepErrorApproach

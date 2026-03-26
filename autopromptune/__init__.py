"""
AutoPromTune
============
LLM-powered prompt disambiguation and tuning tool.

Part of MSc AI thesis research — Eduardo J. Barrios (@edujbarrios)
"""

__version__ = "0.1.0"
__author__ = "Eduardo J. Barrios"
__email__ = "eduardojbarriosgarcia@gmail.com"
__github__ = "https://github.com/edujbarrios/autopromptune"

from .core import PromptTuner

__all__ = ["PromptTuner"]

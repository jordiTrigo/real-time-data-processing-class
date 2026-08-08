"""Safe, resettable incident fixtures for Lesson 12.

The fixtures target Lesson 12's own stack. They never alter the Lesson 11
reference pipeline.
"""

from .catalog import SCENARIOS, Scenario

__all__ = ["SCENARIOS", "Scenario"]

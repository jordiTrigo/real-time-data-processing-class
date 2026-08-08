"""Evidence-first incident response components for Lesson 12.

The package intentionally has no mandatory agent-framework dependency.  It can be
run as a small state graph in class and wrapped by LangGraph when that optional
dependency is installed.
"""

from .models import IncidentReport, IncidentState, Phase, Severity
from .workflow import IncidentWorkflow

__all__ = ["IncidentReport", "IncidentState", "IncidentWorkflow", "Phase", "Severity"]

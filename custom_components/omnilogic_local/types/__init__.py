"""Python type hints for OmniLogic Local integration."""
from typing import NewType

from ..const import OmniModel, OmniType

OmniTypeT = NewType("OmniTypeT", OmniType)
OmniModelT = NewType("OmniModelT", OmniModel)

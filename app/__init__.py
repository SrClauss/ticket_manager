# Application package
import warnings
from warnings import WarningMessage

# Suppress known deprecation warnings from third-party libraries in runtime
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import logging
import sys

# ANSI colors for stdlib fallback
COLORS = {
    'TRACE': '\033[90m',     # Gray
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'SUCCESS': '\033[92m',   # Bright green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[35m',  # Magenta
    'RESET': '\033[0m',
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, '')
        reset = COLORS['RESET']
        record.levelname = f"{color}{record.levelname: <8}{reset}"
        return super().format(record)

# Standard levels for reference:
# CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10

# Add custom levels
# SUCCESS = 25  # Between INFO and WARNING
TRACE = 5     # Below DEBUG
GUI_INFO = 3  # Below TRACE

logging.addLevelName(TRACE, 'TRACE')
logging.addLevelName(GUI_INFO, 'GUI')

# Add methods to Logger class
def gui_info(self, message, *args, **kwargs):
    if self.isEnabledFor(GUI_INFO):
        self._log(GUI_INFO, message, args, stacklevel=2, **kwargs)

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, stacklevel=2, **kwargs)

logging.Logger.gui_info = gui_info
logging.Logger.trace = trace

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(ColoredFormatter('%(levelname)s | %(message)s'))

logger = logging.getLogger('treemonger')
logger.addHandler(handler)
logger.setLevel('INFO')


def set_verbosity(level):
    """Set log level and format based on verbosity (0=INFO, 1=DEBUG, 2+=TRACE)."""
    if level >= 1:
        # Verbose format with file:line
        handler.setFormatter(ColoredFormatter(
            '%(levelname)s | %(filename)s:%(lineno)d | %(message)s'
        ))
    if level == 1:
        logger.setLevel('DEBUG')
    elif level >= 2:
        logger.setLevel('TRACE')


# from loguru import logger
# # Simple format: just colorized level + message
# # Default format (for verbose mode): "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
# logger.remove()  # Remove default handler
# logger.add(sys.stderr, format="<level>{level: <8}</level> | {message}")
# loguru_present = True
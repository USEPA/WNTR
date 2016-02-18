import logging
logging.getLogger('wntr').addHandler(logging.NullHandler())

class _LogWrapper(object):
    initialized = None

    def __init__(self):
        self.logger = logger = logging.getLogger('wntr')
        if not len(self.logger.handlers):
            logger.setLevel(logging.DEBUG)
            # warnings/notes are sent to the final report using the logfile
            self.fh = fh = logging.FileHandler('wntr.log', mode='w') 
            fh.setLevel(logging.WARNING)
            # all info is sent to the screen
            self.ch = ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(name)-12s %(levelname)-8s %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            logger.addHandler(fh)
            logger.addHandler(ch)

def start_logging():
    if _LogWrapper.initialized is None:
        _LogWrapper.initialized = _LogWrapper()

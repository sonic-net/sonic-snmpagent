import json
import logging.handlers
import faulthandler

# configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.NullHandler())

# enable faulthandler to provide more information for debug
# after enable faulthandler, the file 'stderr' will be remembered by faulthandler:
# https://docs.python.org/dev/library/faulthandler.html#issue-with-file-descriptors
faulthandler.enable()

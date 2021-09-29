import logging

from opentelemetry import trace

_LOGGER = None


def get_logger():
    return _LOGGER


def set_logger(logger):
    global _LOGGER
    _LOGGER = logger


set_logger(logging.getLogger("moose"))
logging.basicConfig()


def get_tracer():
    return trace.get_tracer(__name__)
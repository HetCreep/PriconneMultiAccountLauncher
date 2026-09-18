import logging
import threading

logger = logging.getLogger(__name__)


def threading_wrapper(func):
    def _wrapper(self, *arg, **kwargs):
        def runner():
            try:
                func(self, *arg, **kwargs)
            except Exception:
                logger.exception("background thread %s.%s crashed", type(self).__name__, func.__name__)
                raise
        threading.Thread(target=runner, daemon=True, name=f"{type(self).__name__}.{func.__name__}").start()

    return _wrapper

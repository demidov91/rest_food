from functools import wraps
import logging

logger = logging.getLogger(__name__)


def admin_only(f):
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        if not user.is_admin:
            logger.warning('User is not allowed to call %s', f)
            return

        return f(user, *args, **kwargs)

    return wrapper

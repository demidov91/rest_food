from functools import wraps


def admin_only(f):
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        if not user.is_admin:
            return

        return f(user, *args, **kwargs)

    return wrapper

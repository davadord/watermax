from functools import wraps
from flask import render_template
from flask_login import current_user


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.rol not in roles:
                return render_template("errors/403.html"), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

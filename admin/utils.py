from datetime import datetime, date

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_datetime(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        # if date, convert to datetime at midnight
        return val if isinstance(val, datetime) else datetime(val.year, val.month, val.day)
    # try ISO / "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(val)
    except Exception:
        try:
            return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValueError(f"Invalid datetime format: {val}")

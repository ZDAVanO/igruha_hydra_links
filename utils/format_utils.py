from datetime import datetime

def date_to_iso(date_str, date_format="%d.%m.%Y, %H:%M"):
    parsed_date = datetime.strptime(date_str, date_format)
    return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_size(size_in_bytes):
    if size_in_bytes >= 2**30:
        size_in_gb = size_in_bytes / (2**30)
        return f"{size_in_gb:.2f} GB"
    elif size_in_bytes >= 2**20:
        size_in_mb = size_in_bytes / (2**20)
        return f"{size_in_mb:.2f} MB"
    else:
        return f"{size_in_bytes} bytes"

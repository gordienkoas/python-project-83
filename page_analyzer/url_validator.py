import validators

def validate_url(url):
    if not url or len(url) > 255:
        return "Некорректный URL или превышена длина 255 символов."
    elif not validators.url(url):
        return "Некорректный URL."
    return None
from urllib.parse import urlparse


def parse_url(url):
    parsed_url = urlparse(url.strip())
    return f"{parsed_url.scheme}://{parsed_url.netloc}"
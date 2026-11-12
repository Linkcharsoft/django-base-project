import ipaddress

from django.conf import settings


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def get_client_ip(request):
    """Client IP, as seen by the last proxy we trust. ``None`` if it is not a valid IP.

    X-Forwarded-For is read ``TRUSTED_PROXY_COUNT`` hops from the RIGHT: each trusted proxy
    appends the address it received the connection from, so the entry it wrote is reliable and
    everything to its left was written by the client and can be forged. With 0 (no proxy) or no
    header, ``REMOTE_ADDR`` is used. An unparseable hop returns ``None`` rather than reaching a
    ``GenericIPAddressField`` and failing the request.
    """
    proxies = settings.TRUSTED_PROXY_COUNT
    header = request.headers.get("x-forwarded-for", "")
    if proxies and header:
        hops = header.split(",")
        return _valid_ip(hops[-min(proxies, len(hops))])
    return _valid_ip(request.META.get("REMOTE_ADDR") or "")

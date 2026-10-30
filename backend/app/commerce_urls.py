"""Public HTTPS links, validated without fetching arbitrary websites."""
import ipaddress
from urllib.parse import urlsplit


def validated_product_url(value):
    if not isinstance(value,str) or not 1<=len(value)<=2000 or any(ord(c)<33 or c=='\\' for c in value):
        raise ValueError('Use a valid public HTTPS product link, up to 2,000 characters.')
    try:
        parts=urlsplit(value)
        host=(parts.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
        if parts.scheme!='https' or not host or parts.username or parts.password or parts.port not in (None,443):
            raise ValueError()
        try:
            address=ipaddress.ip_address(host)
        except ValueError:
            if '.' not in host or host.split('.')[-1].isdigit() or host.endswith(('.local','.localhost','.internal','.test','.invalid')) or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') or not all(c.isalnum() or c=='-' for c in label) for label in host.split('.')):
                raise ValueError()
        else:
            if not address.is_global or address.is_multicast:
                raise ValueError()
    except (ValueError,UnicodeError):
        raise ValueError('Use a public HTTPS store link, without a login or private network address.') from None
    return value,host

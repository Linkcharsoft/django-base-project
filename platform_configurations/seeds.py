from platform_configurations.models import SystemStatus


def seed():
    # A leftover is_operational=False makes every endpoint answer 503, which
    # reads as "the backend is broken" from the frontend side.
    status = SystemStatus.get_status()
    if not status.is_operational:
        status.is_operational = True
        status.save(update_fields=["is_operational"])
    return "system marked operational"

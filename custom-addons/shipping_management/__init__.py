from . import models
from . import report
from . import wizard


def _post_init_hook(env):
    """Update cron intervals on module upgrade."""
    cron = env.ref(
        "shipping_management.ir_cron_shipping_tracking_update",
        raise_if_not_found=False,
    )
    if cron and cron.interval_number != 2:
        cron.write({"interval_number": 2})

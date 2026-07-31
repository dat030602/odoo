from . import controllers
from . import models


def post_init_hook(env):
    from odoo import api
    from odoo.api import SUPERUSER_ID

    env = api.Environment(env.cr, SUPERUSER_ID, {})
    env["smart.search.config"]._ensure_default_configs()

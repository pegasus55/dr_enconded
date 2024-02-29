# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import wizard
from odoo import api, SUPERUSER_ID


def _assign_group_to_default_user_template(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default_user_template = env['res.users'].with_context(active_test=False).search([
        ('id', '=', 3)
    ])
    group_id = env.ref('hr_dr_management.hr_dr_management_group_employee', raise_if_not_found=False)
    if default_user_template and group_id:
        default_user_template.groups_id = [(4, group_id.id)]
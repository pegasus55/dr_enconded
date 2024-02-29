# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _assign_group_to_default_user_template(cr, registry):
    """
    Esta función busca los dos grupos de permisos que puede tener un usuario y los elimina de los permisos asignados
    al usuario por defecto.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    default_user_template = env['res.users'].with_context(active_test=False).search([
        ('id', '=', 3)
    ])
    group_id = env.ref('hr_recruitment.group_hr_recruitment_manager', raise_if_not_found=False)
    if default_user_template and group_id:
        default_user_template.groups_id = [(3, group_id.id)]
        # default_user_template.groups_id = [(4, False)]

    group_id = env.ref('hr_recruitment.group_hr_recruitment_user', raise_if_not_found=False)
    if default_user_template and group_id:
        default_user_template.groups_id = [(3, group_id.id)]

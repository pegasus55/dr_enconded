# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import wizard
from odoo import api, SUPERUSER_ID


def _archive_salary_rules(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    salary_rule_ids = env['hr.salary.rule'].search([
        ('code', 'in',
         ['BASIC',
          'GROSS',
          'DEDUCTION',
          'ATTACH_SALARY',
          'ASSIG_SALARY',
          'CHILD_SUPPORT',
          'REIMBURSEMENT',
          'NET'])
    ])
    for salary_rule in salary_rule_ids:
        salary_rule.active = False
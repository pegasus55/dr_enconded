# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, float_compare, float_is_zero
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from math import ceil, floor
import re
from calendar import isleap, monthrange


class HrAssetsLiquidation(models.Model):
    _inherit = 'hr.assets.liquidation'
    _description = 'Liquidation of assets table'

    def get_structure_id(self):
        return self.env.ref('hr_dr_payroll_enterprise_ec_private.payroll_structure_assets_liquidation').id

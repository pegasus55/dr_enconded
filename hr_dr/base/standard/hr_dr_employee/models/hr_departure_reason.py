# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class DepartureReason(models.Model):
    _inherit = "hr.departure.reason"

    code = fields.Char(string="Code", required=True)

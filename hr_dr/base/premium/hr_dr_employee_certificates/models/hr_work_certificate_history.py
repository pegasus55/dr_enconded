# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class WorkCertificateHistory(models.Model):
    _name = "hr.work.certificate.history"
    _description = 'Work certificate history'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    _TYPE = [
        ('without_income', 'Without income'),
        ('with_income', 'With income'),
    ]
    type = fields.Selection(_TYPE, string='Type', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", tracking=True)
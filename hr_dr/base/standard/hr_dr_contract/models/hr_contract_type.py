# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ContractType(models.Model):
    _inherit = ['hr.contract.type']

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import template for contract type'),
            'template': '/hr_dr_contract/static/template/Tipo de contrato (hr.contract.type).xlsx'
        }]

    description = fields.Text(string='Description')
    normative_id = fields.Many2one('hr.normative', string="Regulation", required=True, help='')
    active = fields.Boolean(string='Active', default='True', help='')
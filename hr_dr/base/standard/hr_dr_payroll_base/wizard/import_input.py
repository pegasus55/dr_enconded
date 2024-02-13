# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
import base64


class ImportInput(models.TransientModel):
    _name = 'import.input'
    _description = 'Import input'
    _inherit = ['dr.base']

    def action_import_input(self):
        pass

    def _default_template(self):
        template_path = odoo.modules.module.get_resource_path(
            'hr_dr_payroll_base', 'import_template', 'Input.xlsx')
        with open(template_path, 'rb') as imp_sheet:
            file = imp_sheet.read()
        return file and base64.b64encode(file)

    def get_template(self):
        return {
            'name': 'Input',
            'type': 'ir.actions.act_url',
            'url': ("web/content/?model=" + self._name + "&id=" +
                    str(self.id) + "&filename_field=template_name&"
                                   "field=template&download=true&"
                                   "filename=Input.xlsx"),
            'target': 'self',
        }

    data = fields.Binary(string='Archivo', help='Select the input file.')
    template = fields.Binary(string='Template', default=_default_template)
    template_name = fields.Char(default='Input.xlsx')
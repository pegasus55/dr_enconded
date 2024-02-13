# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class L10nLatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'

    code = fields.Char(string='Code')
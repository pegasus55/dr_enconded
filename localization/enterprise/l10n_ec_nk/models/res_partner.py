# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from .utils import additional_check_vat


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def update_identifiers(self):
        sql = """UPDATE res_partner SET vat='9999999999'
        WHERE vat is NULL"""
        self.env.cr.execute(sql)

    def init(self):
        self.update_identifiers()
        super(ResPartner, self).init()

    @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    def check_vat(self):
        for rec in self:
            res = False
            res = additional_check_vat(rec.vat, rec.l10n_latam_identification_type_id.name)
            if not res:
                raise ValidationError('Error in the identification number.')
            partner_ids = self.env['res.partner'].search(
                [
                    ('vat', '=', rec.vat),
                    ('id', '!=', rec.id),
                    ('company_id', '=', rec.company_id.id)
                ])
            if partner_ids:
                raise ValidationError(_('There is already a contact with this identification number.'))
        return super(ResPartner, self).check_vat()
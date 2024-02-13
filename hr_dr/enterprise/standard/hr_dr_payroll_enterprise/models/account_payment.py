# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import os
import logging
from jinja2 import Environment, FileSystemLoader

account_type = {
    'savings': 'AHO',
    'checking': 'CTE',
}

id_type = {
    'Cédula': 'C',
    'RUC': 'R',
    'Pasaporte': 'P',
}


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payroll_payment = fields.Boolean(string="Payroll payment", default=False)
    employee_id = fields.Many2one(string="Collaborator", comodel_name='res.partner')

    def get_cash_management(self):
        partner = self.partner_id or self.employee_id

        bank_id = self.env['res.partner.bank'].search(
            [('partner_id', '=', partner.id)], order="id desc", limit=1)
        if not bank_id:
            raise ValidationError(_("The supplier / collaborator %s does not have a registered bank account."
                                    % partner.name))
        dtc = []
        data = {'employees': ''}
        dtc.append({
            'vat': partner.vat,
            'amount': '%.2f' % self.amount,
            'account_type': account_type.get(bank_id.account_type, ''),
            'account_number': bank_id.acc_number,
            'reference': self.ref or 'PAGO',
            'phone': partner.phone or partner.mobile,
            'month': self.date.month,
            'year': self.date.year,
            'id_type': id_type.get(partner.l10n_latam_identification_type_id.name, ''),
            'name': partner.name,
            'code': bank_id.bank_id.bic,
        })
        if not dtc:
            raise ValidationError(_("No supplier / collaborator has a bank account assigned."))

        data = {'employees': dtc}
        if self.journal_id.bank_id.bic != "":
            template_path = os.path.join(os.path.dirname(__file__), 'banks')
            env = Environment(loader=FileSystemLoader(template_path))
            bank_format = env.get_template(self.journal_id.bank_id.bic + '.xml')
            report = bank_format.render(data)
            buf = io.StringIO()
            buf.write(report)
            out = base64.encodebytes(buf.getvalue().encode('utf-8')).decode()
            logging.error(out)
            buf.close()
            self.cash_management = out
            self.cash_management_name = _('Transfer %s.txt') % partner.name
            return out
        else:
            raise ValidationError(_("The BIC/SWIFT code of the bank associated with the payment journal "
                                    "must be established."))
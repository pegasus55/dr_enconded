# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import os
from jinja2 import Environment, FileSystemLoader
from itertools import groupby

account_type = {
    'savings': 'AHO',
    'checking': 'CTE',
}

id_type = {
    'Cédula': 'C',
    'RUC': 'R',
    'Pasaporte': 'P',
}


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    payroll_payment = fields.Boolean(string="Payroll payment", default=False)

    def get_cash_management(self):
        dtc = []
        data = {'employees': ''}
        bank_account = self.journal_id.bank_account_id

        payment_ids = groupby(self.payment_ids, lambda x: x.partner_id if x.partner_id.id else x.employee_id)
        if not bank_account:
            raise ValidationError(_("The journal does not have a bank account configured, "
                                    "enter it before generating the cash management."))
        for partner, payments in payment_ids:
            if not partner:
                raise ValidationError(_('Payment {} does not have a supplier / partner associated with it.').format(
                    payment.name))

            amount = 0
            for p in list(payments):
                amount += p.amount
                payment = p

            partner_bank = payment.partner_bank_id

            if not id_type.get(partner.l10n_latam_identification_type_id.name, False):
                raise ValidationError(
                    _("The supplier / collaborator {} does not have a "
                      "valid type of identification (ID, RUC, Passport).").format(partner.name))

            name = partner.name.upper().replace('Ñ', 'N').replace('Á', 'A').replace('É', 'E').replace('Í', 'I')\
                .replace('Ó', 'O').replace('Ú', 'U')

            dtc.append({
                'vat': partner.vat,
                'city': partner.city,
                'street': partner.street,
                'amount': '%.2f' % amount,
                'account_type': account_type.get(partner_bank.account_type, ''),
                'account_number': partner_bank.acc_number,
                'reference': payment.ref or 'PAGO',
                'phone': partner.phone or partner.mobile,
                'email': partner.email,
                'month': self.date.month,
                'year': self.date.year,
                'id_type': id_type.get(partner.l10n_latam_identification_type_id.name, ''),
                'name': name,
                'bank_account': bank_account.acc_number,
                'code': partner_bank.bank_id.bic,
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
            buf.close()
            self.cash_management = out
            self.cash_management_name = _('Transfer {}.txt').format(self.journal_id.name)
            return out
        else:
            raise ValidationError(_("The BIC/SWIFT code of the bank associated with the payment journal "
                                    "must be established."))
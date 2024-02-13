# -*- coding: utf-8 -*-

import base64
from cryptography.hazmat.primitives.serialization import pkcs12

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RequestPassphrase(models.TransientModel):
    _name = 'dr_signature.check.passphrase.wizard'
    _description = 'Check passphrase wizard table'

    # def default_user_id(self):
    #     return self.env.uid
    def default_employee_id(self):
        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if employee_id:
            return employee_id.id
        return False

    # user_id = fields.Many2one('res.users', string='User', compute='_compute_user_id', default=default_user_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=default_employee_id)
    has_passphrase = fields.Boolean(compute='_has_passphrase')
    passphrase = fields.Char(string='Passphrase')
    reason = fields.Text(string='Reason', help='Reason of the electronic signature.')
    sign_document = fields.Boolean(string='Sign document', default=True,
                                   help='If this field is not selected, the document wont be signed.')
    has_error = fields.Boolean(default=False)
    error_msg = fields.Char()

    def _clear_message(self):
        self.has_error = False
        self.error_msg = False

    @api.depends('employee_id')
    def _has_passphrase(self):
        for rec in self:
            rec.has_passphrase = True
            if rec.employee_id.id:
                rec.has_passphrase = rec.employee_id.has_passphrase
            if rec.employee_id.store_passphrase and rec.employee_id.passphrase:
                rec.has_passphrase = False

    def action_check(self):
        self._clear_message()
        if 'fw_report' in self._context:
            report = self._context['fw_report']
            if self.sign_document:
                certificate = self.get_certificate()
                if certificate:
                    certificate = base64.decodebytes(certificate)

                    passphrase = self.get_passphrase()
                    if not passphrase:
                        passphrase = ''
                    try:
                        data = pkcs12.load_key_and_certificates(certificate, passphrase.encode())
                    except ValueError as e:
                        if e.args[0] == 'Invalid password or PKCS12 data':
                            # self.has_error = True
                            # self.error_msg = _('Invalid password or PKCS12 data')
                            # return {
                            #     "type": "ir.actions.do_nothing",
                            # }
                            raise ValidationError(_('Invalid password or PKCS12 data'))

                    signature = {
                        'employee_id': self.employee_id.id,
                        'passphrase': passphrase if passphrase else '',
                        'reason': self.reason if self.reason else '',
                        'sign_document': self.sign_document,
                    }

                    if report.get('type', False) == 'ir.actions.act_url':
                        # If the report is an URL actions, pass the data as a GET parameter
                        url = report.get('url', False)
                        if url.find('?') == -1:
                            report['url'] = url + '?signature=' + str(self.id)
                        else:
                            report['url'] = url + '&signature=' + str(self.id)
                    else:

                        if 'context' in report:
                            report['context']['signature'] = signature
                        else:
                            report['context'] = {'signature': signature}

            return report

    def get_certificate(self):
        if self.employee_id.id:
            return self.employee_id.signature_cert
        return False

    def get_passphrase(self):
        if self.employee_id.id:
            if self.employee_id.store_passphrase and self.employee_id.passphrase:
                self.passphrase = self.employee_id.passphrase
            if self.passphrase:
                return self.passphrase
        return False

    # def _compute_user_id(self):
    #     for rec in self:
    #         rec.user_id = self.env.uid
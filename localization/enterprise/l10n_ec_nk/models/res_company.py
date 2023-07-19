# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
import base64
from OpenSSL import crypto
from datetime import datetime
import subprocess
import tempfile
from odoo.exceptions import UserError
KEY_TO_PEM_CMD = "openssl pkcs12 -nocerts -in %s -out %s -passin pass:%s -passout pass:%s"


class ResCompany(models.Model):
    _inherit = 'res.company'

    withholding_agent = fields.Boolean(default=True, string='Withholding agent')
    accountant_id = fields.Many2one('res.partner', 'Accountant')
    identity_legal_representative = fields.Char('Identity card of the legal representative', size=10)
    special_taxpayer = fields.Selection(
        [
            ('Si', 'Si'),
            ('No', 'No')
        ],
        string='Special taxpayer',
        required=True,
        default='No'
    )

    electronic_signature_file = fields.Binary(string='Electronic signature file')
    electronic_signature_password = fields.Char('Electronic signature password')
    issue_type = fields.Selection(
        [
            ('1', 'Normal'),
            ('2', 'Indisponibilidad')
        ],
        string='Issue type',
        required=True,
        default='1'
    )
    environment = fields.Selection(
        [
            ('1', 'Pruebas'),
            ('2', 'Producción')
        ],
        string='Environment',
        required=True,
        default='1'
    )

    electronic_signature_issue_date = fields.Date(string="Date of issue", readonly=True)
    electronic_signature_due_date = fields.Date(string="Due date", readonly=True)
    electronic_signature_serial_number = fields.Char(string="Serial number", readonly=True)
    electronic_signature_owner = fields.Char(string="Owner", readonly=True)
    electronic_signature_issuer = fields.Char(string="Issuer", readonly=True)
    electronic_signature_serial_number_certificate = fields.Char(string="Certificate serial number", readonly=True)
    electronic_signature_version_certificate = fields.Char(string="Certificate version", readonly=True)

    @api.onchange(
        'electronic_signature_file',
        'electronic_signature_password',
    )
    def onchange_electronic_signature(self):
        vals = {
            "electronic_signature_issue_date": False,
            "electronic_signature_due_date": False,
            "electronic_signature_serial_number": False,
            "electronic_signature_owner": False,
            "electronic_signature_issuer": False,
            "electronic_signature_serial_number_certificate": False,
            "electronic_signature_version_certificate": False,
        }
        if self.electronic_signature_file and self.electronic_signature_password:
            file_content = base64.decodebytes(self.electronic_signature_file)
            try:
                p12 = crypto.load_pkcs12(file_content, self.electronic_signature_password)
            except Exception as ex:
                raise UserError(_('Check the electronic signature file or the password entered.'))

            private_key = self.convert_key_cer_to_pem(file_content, self.electronic_signature_password)
            start_index = private_key.find("Signing Key")
            if start_index >= 0:
                private_key = private_key[start_index:]
            start_index = private_key.find("-----BEGIN ENCRYPTED PRIVATE KEY-----")
            cert = p12.get_certificate()
            issuer = cert.get_issuer()
            subject = cert.get_subject()
            vals.update({
                "electronic_signature_issue_date": datetime.strptime(cert.get_notBefore().decode("utf-8"),
                                                                     "%Y%m%d%H%M%SZ"),
                "electronic_signature_due_date": datetime.strptime(cert.get_notAfter().decode("utf-8"),
                                                                   "%Y%m%d%H%M%SZ"),
                "electronic_signature_serial_number": subject.serialNumber,
                "electronic_signature_owner": subject.CN,
                "electronic_signature_issuer": issuer.CN,
                "electronic_signature_serial_number_certificate": cert.get_serial_number(),
                "electronic_signature_version_certificate": cert.get_version(),
            })
        return {
            'value': vals
        }

    def convert_key_cer_to_pem(self, key, password):
        with tempfile.NamedTemporaryFile(
            "wb", suffix=".key", prefix="edi.ec.tmp."
        ) as key_file, tempfile.NamedTemporaryFile("rb", suffix=".key", prefix="edi.ec.tmp.") as key_pem_file:
            key_file.write(key)
            key_file.flush()
            subprocess.call((KEY_TO_PEM_CMD % (key_file.name, key_pem_file.name, password, password)).split())
            key_pem = key_pem_file.read().decode()
        return key_pem
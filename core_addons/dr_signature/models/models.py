# -*- coding: utf-8 -*-

import base64
from cryptography.hazmat.primitives.serialization import pkcs12
from odoo import models, fields, api, _


class DigitalSignature(models.AbstractModel):
    _name = 'dr_signature.base'
    _description = 'Digital Signature base'

    signature_cert = fields.Binary(string="Digital certificate", groups="base.group_system",
                                   help="Upload a P12 file with a digital certificate using PKCS#12 encryption.")
    has_passphrase = fields.Boolean(string="Has passphrase", compute='_compute_has_passphrase', store=True)
    passphrase = fields.Char(string="Passphrase")
    store_passphrase = fields.Boolean(string="Store passphrase", default=False)

    @api.depends('signature_cert')
    def _compute_has_passphrase(self):
        for rec in self:
            rec.has_passphrase = False
            if rec.signature_cert:
                certificate = base64.decodebytes(rec.signature_cert)
                try:
                    data = pkcs12.load_key_and_certificates(certificate, ''.encode())
                except ValueError as e:
                    if e.args[0] == 'Invalid password or PKCS12 data':
                        # TODO: Validar si al subir otro tipo de fichero que no sea .p12 o use otra encriptación entra
                        #  aquí o no y si lo hace validar que no entre.
                        rec.has_passphrase = True

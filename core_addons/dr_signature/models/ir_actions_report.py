# -*- coding: utf-8 -*-

import base64
from datetime import datetime
from io import BytesIO
from pyhanko import stamp
from pyhanko.pdf_utils import text
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields as h_fields, signers
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import logging
from pyhanko_certvalidator.registry import SimpleCertificateStore
from pyhanko.keys import _translate_pyca_cryptography_cert_to_asn1, _translate_pyca_cryptography_key_to_asn1
from cryptography.hazmat.primitives.serialization import pkcs12
logger = logging.getLogger(__name__)


def get_qr_content(name, current_date, reason=False, location=False, url=False, version=False):
    """ Recibe un grupo de parámetros (todos ellos cadenas de texto) y los devuleve en una cadena con el formato
    específico para crear un código QR a partir de ella."""

    data_parts = [
        _('SIGNED BY: {}').format(name),
        _('DATE: {}').format(current_date)
    ]
    if reason:
        data_parts.append(_('REASON: {}').format(reason))
    if location:
        data_parts.append(_('LOCATION: {}').format(location))
    if url:
        data_parts.append(_('VALIDATE WITH: {}').format(url))
    if version:
        data_parts.append(version)

    data = '\n'.join(data_parts)

    # Validating the length of alphanumeric characters is acceptable for a QR code
    # A QR code can store 3KB of data: that's 7089 numeric characters, 4269 alphanumeric characters or 1.817 UTF-16 characters
    limit = 4269
    data_len = len(data)
    if data_len > limit:
        raise ValidationError(_('The limit of alphanumeric characters for a QR image is {}, your content\'s total '
                                'length is {}. Please reduce your data length.').format(limit, data_len))
    return data


class SimpleSigner(signers.SimpleSigner):
    """ Extendiendo la clase SimpleSigner para cargar en el método load_pkcs12 el certificado binario en lugar de la
    ruta del fichero."""

    @classmethod
    def load_pkcs12(
            cls,
            pfx_bytes,
            ca_chain_files=None,
            other_certs=None,
            passphrase=None,
            signature_mechanism=None,
            prefer_pss=False,
    ):
        """
        Load certificates and key material from a PCKS#12 archive
        (usually ``.pfx`` or ``.p12`` files).

        :param pfx_bytes:
            Binary string with PKCS#12 archive.
        :param ca_chain_files:
            Path to (PEM/DER) files containing other relevant certificates
            not included in the PKCS#12 file.
        :param other_certs:
            Other relevant certificates, specified as a list of
            :class:`.asn1crypto.x509.Certificate` objects.
        :param passphrase:
            Passphrase to decrypt the PKCS#12 archive, if required.
        :param signature_mechanism:
            Override the signature mechanism to use.
        :param prefer_pss:
            Prefer PSS signature mechanism over RSA PKCS#1 v1.5 if
            there's a choice.
        :return:
            A :class:`.SimpleSigner` object initialised with key material loaded
            from the PKCS#12 file provided.
        """
        # TODO support MAC integrity checking?

        # try:
        #     with open(pfx_file, 'rb') as f:
        #         pfx_bytes = f.read()
        # except IOError as e:  # pragma: nocover
        #     logger.error(f'Could not open PKCS#12 file {pfx_file}.', exc_info=e)
        #     return None

        ca_chain = (
            cls._load_ca_chain(ca_chain_files) if ca_chain_files else set()
        )
        if ca_chain is None:  # pragma: nocover
            return None
        try:
            (
                private_key,
                cert,
                other_certs_pkcs12,
            ) = pkcs12.load_key_and_certificates(pfx_bytes, passphrase)
        except (IOError, ValueError, TypeError) as e:
            logger.error(
                'Could not load key material from PKCS#12 file', exc_info=e
            )
            return None
        kinfo = _translate_pyca_cryptography_key_to_asn1(private_key)
        cert = _translate_pyca_cryptography_cert_to_asn1(cert)
        other_certs_pkcs12 = set(
            map(_translate_pyca_cryptography_cert_to_asn1, other_certs_pkcs12)
        )

        cs = SimpleCertificateStore()
        certs_to_register = ca_chain | other_certs_pkcs12
        if other_certs is not None:
            certs_to_register |= set(other_certs)
        cs.register_multiple(certs_to_register)
        return SimpleSigner(
            signing_key=kinfo,
            signing_cert=cert,
            cert_registry=cs,
            signature_mechanism=signature_mechanism,
            prefer_pss=prefer_pss,
        )


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    add_signature = fields.Boolean(default=False)
    x_coordinate = fields.Integer(default=200)
    y_coordinate = fields.Integer(default=10)
    signature_width = fields.Integer(default=200)
    signature_height = fields.Integer(default=100)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report_sudo = self._get_report(report_ref)
        pdf_content, file_type = super(IrActionsReport, self)._render_qweb_pdf(report_ref, res_ids, data)

        if report_sudo.add_signature:
            signed_pdf_content = report_sudo.sign_document(pdf_content, file_type, self._context)
            if signed_pdf_content:
                return signed_pdf_content, file_type
        return pdf_content, file_type

    def sign_document(self, pdf_content, file_type, context):
        if file_type == 'pdf':
            if 'signature' in context:
                sign_data = context['signature']
                sign_document = sign_data.get('sign_document', False)
                if sign_document:

                    employee_id = self.env['hr.employee'].sudo().browse(sign_data.get('employee_id'))
                    passphrase = sign_data.get('passphrase', '')
                    reason = sign_data.get('reason', False)

                    cert = base64.decodebytes(employee_id.signature_cert)
                    signer = SimpleSigner.load_pkcs12(cert, passphrase=passphrase.encode())

                    ll_x = 200 if not self.x_coordinate else self.x_coordinate
                    ll_y = 10 if not self.y_coordinate else self.y_coordinate
                    ur_x = ll_x + (200 if not self.signature_width else self.signature_width)
                    ur_y = ll_y + (100 if not self.signature_height else self.signature_height)

                    pages = sign_data.get('pages', [-1])
                    for p in pages:
                        pdf_content_stream = BytesIO(pdf_content)
                        writer = IncrementalPdfFileWriter(pdf_content_stream)
                        field_name = f'Signature_{p}'
                        meta = signers.PdfSignatureMetadata(field_name=field_name)
                        style = stamp.QRStampStyle(
                            stamp_text=_('Digitally signed by:\n%(signer)s\nDate: %(ts)s'),
                            border_width=0,
                            innsep=0,
                            qr_inner_size=100,
                            text_box_style=text.TextBoxStyle(),
                        )

                        h_fields.append_signature_field(
                            writer, sig_field_spec=h_fields.SigFieldSpec(
                                field_name, box=(ll_x, ll_y, ur_x, ur_y), on_page=p))

                        pdf_signer = signers.PdfSigner(meta, signer=signer, stamp_style=style)

                        qr_text = get_qr_content(
                            signer.subject_name, datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                            reason=reason
                        )

                        with BytesIO() as buf:
                            pdf_signer.sign_pdf(writer, output=buf, appearance_text_params={'url': qr_text})
                            buf.seek(0)
                            pdf_content = buf.read()
                    return pdf_content
        return False

    def report_action(self, docids, data=None, config=True):
        """ Hereda report_action para lanzar wizard de passcode si el reporte requiere firma electrónica. """
        report = super(IrActionsReport, self).report_action(docids, data, config)
        if self.add_signature and self.report_type == 'qweb-pdf':
            return {
                'name': _("Electronic signature"),
                'type': 'ir.actions.act_window',
                'res_model': 'dr_signature.check.passphrase.wizard',
                'context': {'fw_report': report},
                'view_mode': 'form',
                'target': 'new',
            }
        return report

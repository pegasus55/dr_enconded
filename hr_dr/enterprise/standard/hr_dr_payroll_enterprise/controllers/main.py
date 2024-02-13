# -*- coding: utf-8 -*-

import io
import re

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo.http import request, route, content_disposition
from odoo.tools.safe_eval import safe_eval
from odoo.addons.hr_payroll.controllers.main import HrPayroll


class CustomHrPayroll(HrPayroll):

    def get_signature_context(self, sid):
        signature = request.env['dr_signature.check.passphrase.wizard'].sudo().browse(sid)
        if signature.id:
            context = {
                'employee_id': signature.employee_id.id,
                'passphrase': signature.passphrase,
                'reason': signature.reason if signature.reason else '',
                'sign_document': signature.sign_document,
            }
            return context
        return {}

    @route(["/print/payslips"], type='http', auth='user')
    def get_payroll_report_print(self, list_ids='', **post):
        sign_context = {}
        sid = post.get('signature', False)
        if sid:
            sign_context = self.get_signature_context(int(sid))
        if not request.env.user.has_group('hr_payroll.group_hr_payroll_user') or not list_ids or re.search("[^0-9|,]", list_ids):
            return request.not_found()

        ids = [int(s) for s in list_ids.split(',')]
        payslips = request.env['hr.payslip'].browse(ids)

        pdf_writer = PdfFileWriter()

        for payslip in payslips:
            if not payslip.struct_id or not payslip.struct_id.report_id:
                report = request.env.ref('hr_payroll.action_report_payslip', False)
            else:
                report = payslip.struct_id.report_id
            context = {'lang': payslip.employee_id.sudo().address_home_id.lang}
            pdf_content, _ = request.env['ir.actions.report'].with_context(context).sudo()\
                ._render_qweb_pdf(report, payslip.id, data={'company_id': payslip.company_id})

            reader = PdfFileReader(io.BytesIO(pdf_content), strict=False, overwriteWarnings=False)

            for page in range(reader.getNumPages()):
                pdf_writer.addPage(reader.getPage(page))

        _buffer = io.BytesIO()
        pdf_writer.write(_buffer)
        merged_pdf = _buffer.getvalue()
        _buffer.close()

        if report:
            sign_context.update({'pages': [i for i in range(len(payslips))]})
            signed_content = report.sign_document(merged_pdf, 'pdf', {'signature': sign_context})
            if signed_content:
                merged_pdf = signed_content

        if len(payslips) == 1 and payslips.struct_id.report_id.print_report_name:
            report_name = safe_eval(payslips.struct_id.report_id.print_report_name, {'object': payslips})
        else:
            report_name = "Payslips"

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf)),
            ('Content-Disposition', content_disposition(report_name + '.pdf'))
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
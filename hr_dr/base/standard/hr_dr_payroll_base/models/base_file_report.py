# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
import base64, io


class BaseFileReport(models.TransientModel):
    """Modelo en memoria para almacenar temporalmente los archivos generados al cargar un reporte.
    Todos los asistentes que generen un archivo (xls, xml, etc.) deben devolver la función show()"""
    _name = 'base.file.report'
    _description = 'Base file report'

    file = fields.Binary('File', readonly=True, required=True)
    filename = fields.Char('File name', readonly=True, required=True)

    def show_excel(self, book, filename):
        buf = io.BytesIO()
        book.save(buf)
        out = base64.encodebytes(buf.getvalue())
        buf.close()
        return self.show(out, filename)

    def show_str(self, str, filename):
        out = base64.encodebytes(str)
        return self.show(out, filename)

    def show(self, file, filename):
        file_report = self.env['base.file.report'].create({'file': file, 'filename': filename})

        return {
            'name': 'Download your file',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': file_report.id,
            'target': 'new',
        }
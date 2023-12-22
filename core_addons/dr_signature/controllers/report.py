# -*- coding: utf-8 -*-

import json
from odoo import http
from odoo.addons.web.controllers.report import ReportController


class ReportControllerInherit(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None, token=None, signature=None):
        if signature is not None and signature != 'false':
            ctx = json.loads(context)
            sig = json.loads(signature)
            ctx['signature'] = sig
            context = json.dumps(ctx)

        return super(ReportControllerInherit, self).report_download(data, context, token)

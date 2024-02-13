# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug
from datetime import datetime
from math import ceil

from odoo import fields, http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import ustr

from odoo.addons.survey.controllers.main import Survey

_logger = logging.getLogger(__name__)


class SurveyInherited(Survey):
    # HELPER METHODS #

    def _check_bad_cases(self, survey, token=None):
        # In case of bad survey, redirect to surveys list
        if not survey.sudo().exists():
            return werkzeug.utils.redirect("/survey/")

        # In case of auth required, block public user
        if survey.auth_required and request.env.user._is_public():
            return request.render("survey.auth_required", {'survey': survey, 'token': token})

        # In case of non open surveys
        if survey.stage_id.closed:
            return request.render("survey.notopen")

        # If there are no pages
        if not survey.page_ids:
            return request.render("survey.nopages", {'survey': survey})

        # If logged user cannot do survey
        # Starting by check if this condition should be evaluated or not
        check_condition = 'True' == request.env['ir.config_parameter'].sudo().get_param('survey.validate.user',
                                                                                        default='False')
        if survey.auth_required and check_condition and not self._user_can_do_survey(token):
            return request.render("hr_dr_appraisal.user_not_allowed", {'username': request.env.user.name})

        # Everything seems to be ok
        return None

    def _user_can_do_survey(self, token):
        """
        Verifies the current survey can be accessed by currently logged in user.
        :param survey: Current survey object ('survey.survey')
        :return: boolean
        """

        # # No token is passed in fill mode so if there is no token, skip this condition returning True
        # if not token:
        #     return True

        # inputs = request.env['survey.user_input'].sudo().search([
        #     ('token', '=', token), ('partner_id', '=', request.env.user.partner_id.id)
        # ])

        inputs = request.env['survey.user_input'].sudo().search([
            ('token', '=', token)
        ])

        for user_input in inputs:
            if user_input.test_entry:  #  Permito que los juegos de prueba siempre pasen
                return True
            if user_input.partner_id == request.env.user.partner_id:    # Valido que el usuario sea el correcto
                return True
        return False


# Survey displaying
    @http.route(['/survey/fill/<model("survey.survey"):survey>/<string:token>',
                 '/survey/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>'],
                type='http', auth='public', website=True)
    def fill_survey(self, survey, token, prev=None, **post):
        """Display and validates a survey"""
        Survey = request.env['survey.survey']
        UserInput = request.env['survey.user_input']

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(survey, token=token)
        if errpage:
            return errpage

        # Load the user_input
        user_input = UserInput.sudo().search([('token', '=', token)], limit=1)
        if not user_input:  # Invalid token
            return request.render("survey.403", {'survey': survey})

        # Do not display expired survey (even if some pages have already been
        # displayed -- There's a time for everything!)
        errpage = self._check_deadline(user_input)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # First page
            page, page_nr, last = Survey.next_page(user_input, 0, go_back=False)
            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        elif user_input.state == 'done':  # Display success message
            return request.render('survey.sfinished', {'survey': survey,
                                                               'token': token,
                                                               'user_input': user_input})
        elif user_input.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = Survey.next_page(user_input, user_input.last_displayed_page_id.id, go_back=flag)

            #special case if you click "previous" from the last page, then leave the survey, then reopen it from the URL, avoid crash
            if not page:
                page, page_nr, last = Survey.next_page(user_input, user_input.last_displayed_page_id.id, go_back=True)

            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        else:
            return request.render("survey.403", {'survey': survey})
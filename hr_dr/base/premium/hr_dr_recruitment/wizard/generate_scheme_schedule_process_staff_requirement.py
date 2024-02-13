# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class GenerateSchemeScheduleProcessStaffRequirement(models.TransientModel):
    _name = "generate.scheme.schedule.process.staff.requirement"
    _description = 'Generate scheme schedule process staff requirement'

    def action_generate_scheme(self):
        if len(self.line_ids) == 0:
            raise UserError(_('You must select at least one stage.'))

        if self.generate_mode == 'by_position':
            if len(self.position_ids) == 0:
                raise UserError(_('You must select at least one position.'))

            for position in self.position_ids:
                for line in self.line_ids:
                    self.env['hr.scheme.schedule.process.staff.requirement'].sudo().create({
                        'mode': self.generate_mode,
                        'position_id': position.id,
                        'sequence': line.sequence,
                        'stage_id': line.stage_id.id,
                        'working_days': line.working_days,
                        'employee_ids': line.employee_ids.ids,
                    })

        elif self.generate_mode == 'by_job':
            if len(self.job_ids) == 0:
                raise UserError(_('You must select at least one job.'))

            for job in self.job_ids:
                for line in self.line_ids:
                    self.env['hr.scheme.schedule.process.staff.requirement'].sudo().create({
                        'mode': self.generate_mode,
                        'job_id': job.id,
                        'sequence': line.sequence,
                        'stage_id': line.stage_id.id,
                        'working_days': line.working_days,
                        'employee_ids': line.employee_ids.ids,
                    })

        tree_view_id = self.env.ref('hr_dr_recruitment.hr_scheme_schedule_process_staff_requirement_view_tree').id
        form_view_id = self.env.ref('hr_dr_recruitment.hr_scheme_schedule_process_staff_requirement_view_form').id
        search_view_id = self.env.ref('hr_dr_recruitment.hr_scheme_schedule_process_staff_requirement_view_search').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scheme schedule process staff requirement',
            'res_model': 'hr.scheme.schedule.process.staff.requirement',
            'target': 'current',
            'view_mode': 'tree',
            'search_view_id': [search_view_id, 'search'],
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')]
        }

    @api.onchange('generate_mode')
    def _onchange_generate_mode(self):
        self.position_ids = [(6, 0, [])]
        self.job_ids = [(6, 0, [])]

    _GENERATE_MODE = [
        ('by_position', 'By position'),
        ('by_job', 'By job'),
    ]
    generate_mode = fields.Selection(_GENERATE_MODE, string='Generate mode', required=True, default='by_position',
                                     help='')
    position_ids = fields.Many2many('hr.position', 'scheme_process_staff_requirement_position_rel',
                                    'scheme_process_staff_requirement_id', 'position_id', string='Positions')
    job_ids = fields.Many2many('hr.job', 'scheme_process_staff_requirement_job_rel',
                               'scheme_process_staff_requirement_id', 'job_id', string='Jobs')
    line_ids = fields.One2many('generate.scheme.schedule.process.staff.requirement.line', 'wizard_id', 'Stages')


class GenerateSchemeScheduleProcessStaffRequirementLine(models.TransientModel):
    _name = "generate.scheme.schedule.process.staff.requirement.line"
    _description = 'Generate scheme schedule process staff requirement detail'

    wizard_id = fields.Many2one('generate.scheme.schedule.process.staff.requirement', 'Wizard')
    stage_id = fields.Many2one('hr.recruitment.stage', string="Stage", required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    working_days = fields.Integer(string='Number of working days', required=True)
    employee_ids = fields.Many2many('hr.employee', 'scheme_process_staff_requirement_line_employee_rel',
                                    'scheme_process_staff_requirement_line_id', 'employee_id', string='Collaborators')
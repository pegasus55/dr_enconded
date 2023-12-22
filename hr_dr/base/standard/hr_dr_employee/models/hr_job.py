# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Job(models.Model):
    _inherit = 'hr.job'

    @api.onchange('position_id')
    def _onchange_position_id(self):
        if self.position_id:
            if self.description == "":
                self.description = self.position_id.description

    @api.depends('position_id', 'department_id')
    def _compute_job_name(self):
        for job in self:
            if job.position_id and job.department_id:
                job.name = "{} / {}".format(job.position_id.name, job.department_id.name)
            elif job.position_id:
                job.name = "{} / -".format(job.position_id.name)
            elif job.department_id:
                job.name = "- / {}".format(job.department_id.name)
            else:
                job.name = "- / -"

    position_id = fields.Many2one('hr.position', string='Position', required=True)
    name = fields.Char(string='Job position', required=True, index=True, translate=True, compute=_compute_job_name)
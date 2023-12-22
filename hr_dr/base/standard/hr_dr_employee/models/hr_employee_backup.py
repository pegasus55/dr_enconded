# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class EmployeeBackup(models.Model):
    _name = 'hr.employee.backup'
    _description = 'Employee backup'
    _inherit = ['mail.thread']
    _order = "employee_id"

    employee_id = fields.Many2one('hr.employee', string="Collaborator", required=True, ondelete='cascade',
                                  tracking=True)
    employee_backup_id = fields.Many2one('hr.employee', string='Backup', change_default=True, ondelete='restrict',
                                         required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_backup_id.department_id',
                                    readonly=True)
    job_id = fields.Many2one('hr.job', string='Job', related='employee_backup_id.job_id', readonly=True)
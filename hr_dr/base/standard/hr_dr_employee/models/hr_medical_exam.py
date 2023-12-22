# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MedicalExam(models.Model):
    _name = 'hr.medical.exam'
    _description = 'Medical exam'
    _inherit = ['mail.thread']
    _order = "employee_id"

    _TYPE = [
        ('entry', _('Entry')),
        ('regular', _('Regular')),
        ('exit', _('Exit')),
    ]
    type = fields.Selection(_TYPE, string='Type', help='', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, tracking=True)
    height = fields.Float(string='Height (cm)', tracking=True)
    weight = fields.Float(string='Weight (kg)', tracking=True)
    temperature = fields.Float(string='Temperature (°C)', tracking=True)
    pulse = fields.Integer(string='Pulse', tracking=True)
    breathing_frequency = fields.Integer(string='Breathing frequency', tracking=True)
    minimum_blood_pressure = fields.Integer(string='Minimum blood pressure', tracking=True)
    maximum_blood_pressure = fields.Integer(string='Maximum blood pressure', tracking=True)
    employee_id = fields.Many2one('hr.employee', string="Collaborator", ondelete='cascade', required=True, tracking=True)
    backup_document = fields.Many2many('ir.attachment', 'medical_exam_ir_attachment_rel', 'medical_exam_id',
                                       'attachment_id', string="Backup documents", tracking=True)
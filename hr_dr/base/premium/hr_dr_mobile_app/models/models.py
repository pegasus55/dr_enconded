# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Employee(models.Model):
    _inherit = 'hr.employee'

    allow_attendance_mobile = fields.Boolean(string='Allow attendance mobile', default=True, tracking=True) # Permitir asistencia móvil
    attendance_mobile_without_place_restriction = fields.Boolean(string='Attendance mobile without place restriction', tracking=True, help='', default=False)
    place_attendance_ids = fields.Many2many('hr.place.attendance', string="Places allowed to register attendance", tracking=True)

class PlaceAttendance(models.Model):
    _name = 'hr.place.attendance'
    _description = 'Hr Place Attendance'
    _inherit = ['mail.thread']

    name = fields.Char(string="Name", required=True, tracking=True)
    latitude = fields.Float(string='Latitude', required=True, tracking=True)
    longitude = fields.Float(string='Longitude', required=True, tracking=True)
    range_radius = fields.Integer(string='Range radius', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, help='')


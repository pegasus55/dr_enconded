# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class OccupationalStructureLevel(models.Model):
    _name = 'hr.occupational.structure.level'
    _description = 'Occupational structure level'
    _inherit = ['mail.thread']
    _order = "name"

    name = fields.Char(string="Name", tracking=True, required=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class OccupationalStructure(models.Model):
    _name = 'hr.occupational.structure'
    _description = 'Occupational structure'
    _inherit = ['mail.thread']
    _order = "occupational_structure_level_id,name"

    name = fields.Char(string="Name", tracking=True, required=True)
    occupational_structure_level_id = fields.Many2one('hr.occupational.structure.level',
                                                      string='Occupational structure level', tracking=True,
                                                      required=True, ondelete="cascade")
    active = fields.Boolean(string='Active', default=True, tracking=True)


class SectorCommission(models.Model):
    _name = 'hr.sector.commission'
    _description = 'Sector commission'
    _inherit = ['mail.thread']
    _order = "number"

    number = fields.Integer(string="Number", tracking=True, required=True)
    name = fields.Char(string="Name", tracking=True, required=True)
    branch_economic_activity_ids = fields.One2many('hr.branch.economic.activity', 'sector_commission_id',
                                                   string='Branch of economic activities')
    active = fields.Boolean(string='Active', default=True, tracking=True)


class BranchEconomicActivity(models.Model):
    _name = 'hr.branch.economic.activity'
    _description = 'Branch of economic activity'
    _inherit = ['mail.thread']
    _order = "sector_commission_id,number"

    number = fields.Integer(string="Number", tracking=True, required=True)
    name = fields.Text(string="Name", tracking=True, required=True)
    sector_commission_id = fields.Many2one('hr.sector.commission', string='Sector commission', tracking=True,
                                           required=True, ondelete="cascade")
    active = fields.Boolean(string='Active', default=True, tracking=True)


class SubbranchEconomicActivity(models.Model):
    _name = 'hr.subbranch.economic.activity'
    _description = 'Subbranch of economic activity'
    _inherit = ['mail.thread']
    _order = "branch_economic_activity_id,number"

    number = fields.Integer(string="Number", tracking=True, required=True)
    name = fields.Text(string="Name", tracking=True, required=True)
    branch_economic_activity_id = fields.Many2one('hr.branch.economic.activity', string='Branch economic activity',
                                                  tracking=True, required=True, ondelete="cascade")
    active = fields.Boolean(string='Active', default=True, tracking=True)


class SectorTable(models.Model):
    _name = 'hr.sector.table'
    _description = 'Sector table'
    _inherit = ['mail.thread']
    _rec_name = 'IESS_code'
    _order = "sector_commission_id"

    @api.depends('mode', 'sector_table_year_ids', 'sector_table_year_ids.year',
                 'sector_table_year_ids.minimum_salary', 'sector_table_year_ids.minimum_fee')
    def compute_last_values(self):
        for record in self:
            sector_table_year = self.env['hr.sector.table.year'].search([('sector_table_id', '=', record.id)],
                                                                        order="year desc", limit=1)
            if sector_table_year:
                record.last_year = sector_table_year.year
                if record.mode == 'minimum_salary':
                    record.last_minimum_salary = sector_table_year.minimum_salary
                    record.last_minimum_fee = 0
                else:
                    record.last_minimum_salary = 0
                    record.last_minimum_fee = sector_table_year.minimum_fee
            else:
                record.last_minimum_salary = 0
                record.last_minimum_fee = 0
                record.last_year = 0

    sector_commission_id = fields.Many2one('hr.sector.commission', string='Sector commission', tracking=True,
                                           required=True)
    branch_economic_activity_ids = fields.Many2many('hr.branch.economic.activity', string="Branch economic activity")
    subbranch_economic_activity_ids = fields.Many2many('hr.subbranch.economic.activity',
                                                       string="Subbranch economic activity")
    position_id = fields.Text(string='Position / Activity', tracking=True, required=True)
    occupational_structure_id = fields.Many2one('hr.occupational.structure', string='Occupational structure',
                                                tracking=True, required=True)
    comment = fields.Text(string="Comment", tracking=True)
    IESS_code = fields.Char(string="IESS code", tracking=True, required=True)
    _MODE = [
        ('minimum_salary', _('Minimum salary')),
        ('minimum_fee', _('Minimum fee')),
    ]
    mode = fields.Selection(_MODE, string='Mode', tracking=True, default="minimum_salary")
    sector_table_year_ids = fields.One2many('hr.sector.table.year', 'sector_table_id', string='Sector table by years')
    last_year = fields.Integer(string='Last year', tracking=True, compute='compute_last_values')
    last_minimum_salary = fields.Float(string='Last minimum salary', tracking=True, digits='Contract',
                                       compute='compute_last_values')
    last_minimum_fee = fields.Float(string='Last minimum fee', tracking=True, digits='Contract 4',
                                    compute='compute_last_values')
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True,
                                  related='company_id.currency_id')


class SectorTableYear(models.Model):
    _name = 'hr.sector.table.year'
    _description = 'Sector table by year'
    _inherit = ['mail.thread']
    _order = "sector_table_id,year desc"

    sector_table_id = fields.Many2one('hr.sector.table', string='Sector table', tracking=True, required=True,
                                      ondelete="cascade")
    mode = fields.Selection(string='Mode', tracking=True, related='sector_table_id.mode')
    year = fields.Integer(string='Year', tracking=True, required=True)
    minimum_salary = fields.Float(string='Minimum salary', tracking=True, digits='Contract')
    minimum_fee = fields.Float(string='Minimum fee', tracking=True, digits='Contract 4')
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployeeSkill(models.Model):
    _inherit = "hr.employee.skill"

    skill_category_id = fields.Many2one('hr.skill.category', string="Skill category", required=True)

    @api.onchange('skill_category_id')
    def _onchange_skill_category_id(self):
        if self.skill_category_id and self.skill_category_id != self.skill_type_id.skill_category_id:
            self.skill_type_id = False
            self.skill_id = False
            self.skill_level_id = False

    @api.onchange('skill_type_id')
    def _onchange_skill_type_id(self):
        # Establecer los padres
        if self.skill_type_id.skill_category_id:
            self.skill_category_id = self.skill_type_id.skill_category_id

        if self.skill_type_id and self.skill_type_id != self.skill_id.skill_type_id:
            self.skill_id = False
        if self.skill_type_id and self.skill_type_id != self.skill_level_id.skill_type_id:
            self.skill_level_id = False

    @api.onchange('skill_id')
    def _onchange_skill_id(self):
        # Establecer los padres
        if self.skill_id.skill_type_id:
            self.skill_type_id = self.skill_id.skill_type_id

        self.skill_level_id = False

    def validate_module(self):
        """
        Valida que esté instalado el módulo de licencias o lanza un error de lo contrario
        :return:
        """
        if 'dr_start_system' not in self.env.registry._init_modules:
            raise ValidationError(_('Start system [dr_start_system] module must be installed in the system.'))
        if 'dr_license_customer' not in self.env.registry._init_modules:
            raise ValidationError(_('License customer [dr_license_customer] '
                                    'module must be installed in the system.'))

    @api.model
    def create(self, vals):
        self.validate_module()
        return super(HrEmployeeSkill, self).create(vals)

    def write(self, vals):
        self.validate_module()
        return super(HrEmployeeSkill, self).write(vals)

    def unlink(self):
        self.validate_module()
        return super(HrEmployeeSkill, self).unlink()


class HrPosition(models.Model):
    _inherit = "hr.position"

    minimal_skill_ids = fields.One2many('hr.minimal.skill', 'position_id', string="Minimal skills")


class HrMinimalSkill(models.Model):
    _name = "hr.minimal.skill"
    _inherit = ['mail.thread']
    _description = 'Hr Minimal Skill Per Position'
    _order = 'position_id, skill_category_id, skill_type_id, level_progress'

    position_id = fields.Many2one('hr.position', string="Position", required=True, ondelete='cascade', tracking=True)
    skill_category_id = fields.Many2one('hr.skill.category', string="Skill category", required=True, tracking=True)
    skill_type_id = fields.Many2one('hr.skill.type', string="Skill type", required=True,
                                    domain="[('skill_category_id', '=?', skill_category_id)]", tracking=True)
    skill_id = fields.Many2one('hr.skill', string="Skill", required=True,
                               domain="[('skill_type_id', '=?', skill_type_id)]", tracking=True)
    skill_level_id = fields.Many2one('hr.skill.level', string="Required level", required=True,
                                     domain="[('skill_type_id', '=', skill_type_id)]", tracking=True)
    level_progress = fields.Integer(related='skill_level_id.level_progress', string="%")

    _sql_constraints = [
        ('_unique_position_skill', 'unique (position_id, skill_id)', "Two levels for the same skill is not allowed."),
    ]

    @api.constrains('skill_id', 'skill_type_id')
    def _check_skill_type(self):
        for record in self:
            if record.skill_id not in record.skill_type_id.skill_ids:
                raise HrMinimalSkill(_("The skill %(name)s and skill type %(type)s doesn't match.",
                                       name=record.skill_id.name, type=record.skill_type_id.name))

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        for record in self:
            if record.skill_level_id not in record.skill_type_id.skill_level_ids:
                raise HrMinimalSkill(_("The skill level %(level)s is not valid for skill type: %(type)s.",
                                       level=record.skill_level_id.name, type=record.skill_type_id.name))

    @api.onchange('skill_category_id')
    def _onchange_skill_category_id(self):
        if self.skill_category_id and self.skill_category_id != self.skill_type_id.skill_category_id:
            self.skill_type_id = False
            self.skill_id = False
            self.skill_level_id = False

    @api.onchange('skill_type_id')
    def _onchange_skill_type_id(self):
        # Establecer los padres
        if self.skill_type_id.skill_category_id:
            self.skill_category_id = self.skill_type_id.skill_category_id

        if self.skill_type_id and self.skill_type_id != self.skill_id.skill_type_id:
            self.skill_id = False
        if self.skill_type_id and self.skill_type_id != self.skill_level_id.skill_type_id:
            self.skill_level_id = False

    @api.onchange('skill_id')
    def _onchange_skill_id(self):
        # Establecer los padres
        if self.skill_id.skill_type_id:
            self.skill_type_id = self.skill_id.skill_type_id

        self.skill_level_id = False


class HrSkillCategory(models.Model):
    _name = "hr.skill.category"
    _inherit = ['mail.thread']
    _description = 'Hr Skill Category'

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)


class SkillType(models.Model):
    _inherit = 'hr.skill.type'

    skill_category_id = fields.Many2one('hr.skill.category', string='Skill category', required=True)
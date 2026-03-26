# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class CommonEquipment(models.Model):
    _name = "common.equipment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Equipment"

    name = fields.Char("Name", copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    technical_details = fields.Char("Technical Details", copy=False)
    status = fields.Char("Current Status", copy=False)
    date_commencement = fields.Date("Date of Commencement", copy=False)
    equipment_type = fields.Char("Type of Equipment", copy=False)
    site_id = fields.Many2one('res.branch', string='Site', copy=False)
    expense_history_ids = fields.One2many("expense.history", "common_equipment_id", string="Expense History", copy=False)
    meter_reading_ids = fields.One2many("meter.reading", "common_equipment_id", string="Meter Readings", copy=False)
    # maintenance_history_ids = fields.One2many("maintenance.history", "common_equipment_id", string="Maintenance History", copy=False)
    fsm_task_ids = fields.One2many('project.task', 'equipment_id', string='Tasks', help='Tasks generated from this Equipment', domain=[('is_fsm', '=', True)], copy=False)
    fsm_task_count = fields.Integer(compute='_compute_fsm_task_count')

    @api.depends('fsm_task_ids')
    def _compute_fsm_task_count(self):
        equipment_groups = self.env['project.task'].read_group([('is_fsm', '=', True), ('equipment_id', '!=', False)], ['id:count_distinct'], ['equipment_id'])
        equipment_count_mapping = dict(map(lambda group: (group['equipment_id'][0], group['equipment_id_count']), equipment_groups))
        for equipment in self:
            equipment.fsm_task_count = equipment_count_mapping.get(equipment.id, 0)

    def action_view_fsm_tasks(self):
        fsm_form_view = self.env.ref('project.view_task_form2')
        fsm_list_view = self.env.ref('industry_fsm.project_task_view_list_fsm')
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'context': {
                'create': False,
            },
        }

        if len(self.fsm_task_ids) == 1:
            action.update(res_id=self.fsm_task_ids[0].id, views=[(fsm_form_view.id, 'form')])
        else:
            action.update(domain=[('id', 'in', self.fsm_task_ids.ids)], views=[(fsm_list_view.id, 'tree'), (fsm_form_view.id, 'form')], name=_('Tasks from Equipments'))
        return action

    def action_create_maintenance_activity(self):
        self.ensure_one()
        fsm_project_id = self.env['project.project'].sudo().search([('is_fsm', '=', True)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create a Field Service task'),
            'res_model': 'equipment.create.fsm.task',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'use_fsm': True,
                'default_equipment_id': self.id,
                'default_user_id': False,
                'default_name': self.name,
                'default_project_id': fsm_project_id.id,
            }
        }
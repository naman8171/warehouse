# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HelpdeskCreateTask(models.TransientModel):
    _inherit = 'helpdesk.create.fsm.task'

    partner_name = fields.Char("Resident Name", copy=False, related='helpdesk_ticket_id.partner_name')
    partner_email = fields.Char("Email", copy=False, related='helpdesk_ticket_id.partner_email')
    partner_phone = fields.Char("Phone", copy=False, related='helpdesk_ticket_id.partner_phone')
    flat_type = fields.Many2one("flat.type", string="Flat Type", copy=False, related='helpdesk_ticket_id.flat_type')
    site_id = fields.Many2one('res.branch', string='Site', copy=False, related='helpdesk_ticket_id.site_id')
    appartment_status = fields.Selection([('Vacant', 'Vacant'), ('Occupied', 'Occupied'), ('Consficated', 'Consficated')], string="Apartment Status", related='helpdesk_ticket_id.appartment_status')
    ticket_type_id = fields.Many2one("helpdesk.ticket.type", string='Type', copy=False, related='helpdesk_ticket_id.ticket_type_id')
    description = fields.Html(related='helpdesk_ticket_id.description')

    def _generate_task_values(self):
        self.ensure_one()
        facility_manager_id = self.site_id.facility_manager_id
        return {
            'name': self.name,
            'helpdesk_ticket_id': self.helpdesk_ticket_id.id,
            'project_id': self.project_id.id,
            'partner_id': self.partner_id.id,
            'description': self.description,
            'user_id': facility_manager_id.id,
            'fs_type': self.ticket_type_id.id,
            'partner_name': self.partner_name,
            'partner_email': self.partner_email,
            'partner_phone': self.partner_phone,
            'partner_email': self.partner_email,
            'flat_type': self.flat_type.id,
            'site_id': self.site_id.id,
            'appartment_status': self.appartment_status,
        }

    def action_generate_task(self):
        self.ensure_one()
        res = super(HelpdeskCreateTask, self).action_generate_task()
        progress_stage_id = self.env.ref('helpdesk.stage_in_progress')
        if progress_stage_id:
            self.helpdesk_ticket_id.stage_id = progress_stage_id.id
        facility_manager_id = self.site_id.facility_manager_id
        res.user_ids = [(6, 0, facility_manager_id.ids)]
        if facility_manager_id:
            res.activity_schedule('ag_field_service.mail_activity_assign_technician', user_id=facility_manager_id.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=project.task' % res.id
            template_id = self.env.ref('ag_field_service.ag_assign_technician_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': facility_manager_id.email,
                    'name': facility_manager_id.name,
                    'url': url,
                })
            mail_id = template_id.with_context(ctx).send_mail(res.id, force_send=True)
        return res


class EquipmentCreateTask(models.TransientModel):
    _name = 'equipment.create.fsm.task'
    _description = 'Create a Field Service task'

    equipment_id = fields.Many2one('common.equipment', string='Related Equipment', required=True)
    company_id = fields.Many2one(related='equipment_id.company_id')
    name = fields.Char('Title', required=True)
    project_id = fields.Many2one('project.project', string='Project', help='Project in which to create the task', required=True, domain="[('company_id', '=', company_id), ('is_fsm', '=', True)]")
    site_id = fields.Many2one('res.branch', string='Site', copy=False, related='equipment_id.site_id')
    description = fields.Html()

    @api.model
    def default_get(self, fields_list):
        defaults = super(EquipmentCreateTask, self).default_get(fields_list)
        if 'project_id' in fields_list and not defaults.get('project_id'):
            task_default = self.env['project.task'].with_context(fsm_mode=True).default_get(['project_id'])
            defaults.update({'project_id': task_default.get('project_id', False)})
        return defaults

    def _generate_task_values(self):
        self.ensure_one()
        facility_manager_id = self.site_id.facility_manager_id
        fs_type_id = self.env['helpdesk.ticket.type'].sudo().search([('scope', '=', 'common_area_maintenance')], limit=1)
        return {
            'name': self.name,
            'equipment_id': self.equipment_id.id,
            'project_id': self.project_id.id,
            'description': self.description,
            'user_id': facility_manager_id.id,
            'fs_type': fs_type_id.id,
            'site_id': self.site_id.id,
        }

    def action_generate_task(self):
        self.ensure_one()
        facility_manager_id = self.site_id.facility_manager_id
        res = self.env['project.task'].create(self._generate_task_values())
        if facility_manager_id:
            res.activity_schedule('ag_field_service.mail_activity_assign_technician', user_id=facility_manager_id.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=project.task' % res.id
            template_id = self.env.ref('ag_field_service.ag_assign_technician_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': facility_manager_id.email,
                    'name': facility_manager_id.name,
                    'url': url,
                })
            mail_id = template_id.with_context(ctx).send_mail(res.id, force_send=True)
        return res

    def action_generate_and_view_task(self):
        self.ensure_one()
        new_task = self.action_generate_task()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks from Equipments'),
            'res_model': 'project.task',
            'res_id': new_task.id,
            'view_mode': 'form',
            'view_id': self.env.ref('project.view_task_form2').id,
            'context': {
                'fsm_mode': True,
            }
        }

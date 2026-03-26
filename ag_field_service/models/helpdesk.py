# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.osv import expression
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, timedelta

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'

    flat_type = fields.Many2one("flat.type", string="Flat Type", copy=False)
    site_id = fields.Many2one('res.branch', string='Site', copy=False)
    scope_work_id = fields.Many2one("scope.work", string="Scope of Work")
    fs_type_scope = fields.Selection(related="ticket_type_id.scope", store=True)
    appartment_status = fields.Selection([('Vacant', 'Vacant'), ('Occupied', 'Occupied'), ('Consficated', 'Consficated')], string="Apartment Status", copy=False)

    @api.model
    def create(self, vals):
        res = super(HelpdeskTicket, self).create(vals)
        res.user_id = res.create_uid.id
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            stage_id = self.env['helpdesk.stage'].sudo().browse(vals.get('stage_id'))
            if stage_id.is_close:
                domain = [
                    ('res_model', '=', 'helpdesk.ticket'),
                    ('res_id', 'in', self.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_close_ticket').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    activities.sudo().action_feedback(feedback="Ticket Solved")
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=%s&view_type=form&model=helpdesk.ticket' % self.id
                template_id = self.env.ref('ag_field_service.ag_ticket_closure_email_template')
                ctx = dict(self.env.context or {})
                ctx.update({
                        'email_to': self.partner_email,
                        'name': self.partner_name,
                        'url': url,
                    })
                mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)
        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.contact_type == 'Resident':
            self.flat_type = self.partner_id.flat_type.id
            self.site_id = self.partner_id.branch_id.id
            self.appartment_status = self.partner_id.appartment_status
            if self.partner_id.residence_type == 'Landlord':
                self.partner_name = self.partner_id.landlord_name
                self.partner_email = self.partner_id.landlord_email
                self.partner_phone = self.partner_id.landlord_contact
            elif self.partner_id.residence_type == 'Tenant':
                self.partner_name = self.partner_id.tenant_name
                self.partner_email = self.partner_id.tenant_email
                self.partner_phone = self.partner_id.tenant_contact

class HelpdeskTicketType(models.Model):
    _inherit = 'helpdesk.ticket.type'

    scope = fields.Selection([('daily_requests', 'Daily Requests'),
                              ('flat_maintenance', 'Flat Maintenance'),
                              ('general_suggestion', 'General Suggestion'),
                              ('general_complaints', 'General Complaints'),
                              ('general_compliments', 'General Compliments'),
                              ('common_area_maintenance', 'Common Area Maintenance')], string="Scope", default="daily_requests")

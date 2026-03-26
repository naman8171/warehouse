# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorbillApprover(models.Model):
    _name = 'vendorbill.approver'
    _description = 'Vendor bill Approver'

    _check_company_auto = True

    user_id = fields.Many2one('res.users', string="User", required=True, check_company=True)#, domain="[('id', 'not in', existing_request_user_ids)]"
#     existing_request_user_ids = fields.Many2many('res.users', compute='_compute_existing_request_user_ids')
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], string="Status", default="new", readonly=True)
    move_id = fields.Many2one('account.move', string="Bill",
        ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        string='Company', related='move_id.company_id',
        store=True, readonly=True, index=True)

    def action_approve(self):
        self.move_id.action_approve(self)

    def action_refuse(self):
        self.move_id.action_refuse(self)

    def _create_activity(self):
        for approver in self:
            approver.move_id.activity_schedule(
                'ag_field_service.mail_activity_bill_approval',
                user_id=approver.user_id.id)

#     @api.depends('move_id.request_owner_id', 'move_id.approver_ids.user_id')
#     def _compute_existing_request_user_ids(self):
#         for approver in self:
#             approver.existing_request_user_ids = \
#                 self.mapped('move_id.approver_ids.user_id')._origin \
#               | self.move_id.request_owner_id._origin

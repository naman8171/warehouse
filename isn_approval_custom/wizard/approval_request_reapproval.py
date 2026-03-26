# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ApprovalRequestReapproval(models.TransientModel):
    _name = "approval.request.reapproval"
    _description = "Approval Request Reapproval"
    
    reason = fields.Char('Reason')


    def approval_confirm(self):
        app_req_rec = self.env['approval.request'].browse(self._context.get('active_id'))
        
        approver = app_req_rec.mapped('approver_ids').filtered(lambda approver: approver.status == 'refused')
        approver.sudo().write({'status':'pending'})
        app_req_rec.reapprove_request = True
        app_req_rec.activity_schedule(
                'approvals.mail_activity_data_approval',
                summary="Reapproval Request",
                note=self.reason,
                user_id=approver.user_id.id)














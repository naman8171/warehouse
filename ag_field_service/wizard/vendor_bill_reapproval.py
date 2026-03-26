# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class VendorBillReapproval(models.TransientModel):
    _name = "vendor.bill.reapproval"
    _description = "Vendor Bill Reapproval"
    
    reason = fields.Char('Reason')


    def approval_confirm(self):
        acc_move_rec = self.env['account.move'].browse(self._context.get('active_id'))
        
        approver = acc_move_rec.mapped('approver_ids').filtered(lambda approver: approver.status == 'refused')
        acc_move_rec.reapprove_request = True
        acc_move_rec.activity_schedule(
                'ag_field_service.mail_activity_bill_approval',
                summary="Reapproval Request",
                note=self.reason,
                user_id=approver.user_id.id)

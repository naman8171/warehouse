# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'


    def action_create_payments(self):
        acc_move_rec = self.env['account.move'].browse(self._context.get('active_id'))
        if acc_move_rec.move_type == 'in_invoice':
            domain = [
                ('res_model', '=', 'account.move'),
                ('res_id', 'in', acc_move_rec.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_bill_reg_payment').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Payment Processed")
        
        res = super(AccountPaymentRegister, self).action_create_payments()
        return res
# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection([('purchase', 'RFQ Need Application'),
                                        ('payment','Payment Application'),
                                        ('direct_procurement','Direct Procurement Application')], string="Approval Type")    
    
    to_process_payment_user_id = fields.Many2many(
                       'res.users','to_process_payment_user_id_rel','process_payment_user_ref','process_payment_ref', string='Accounts Department Rep',
                        domain=lambda self: [('groups_id', 'in', self.env.ref('account.group_account_user').id)], tracking=True)
    
    

    @api.onchange('approval_type')
    def _onchange_approval_type(self):
        res = super(ApprovalCategory, self)._onchange_approval_type()
        if self.approval_type == 'payment':
            self.has_amount = 'required'
            self.has_payment_method = 'required'
            self.has_date = 'required'
        return res

# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

class PaymentApprovalEntry(models.TransientModel):
    _name = "payment.approval.entry"
    
    
    @api.model
    def _get_default_journal(self):
        domain = [('company_id', '=', self.env.company.id), ('type', 'in', ['general'])]
        journal = self.env['account.journal'].search(domain, limit=1)
        return journal
    
#     @api.model
#     def _get_default_currency(self):
#         journal = self._get_default_journal()
#         return journal.currency_id or journal.company_id.currency_id
    
    
    company_id = fields.Many2one(
        'res.company', 'Company',
        index=True, default=lambda s: s.env.company)
    
#     currency_id = fields.Many2one('res.currency',
#         string='Currency',
#         default=_get_default_currency)
#     account_id = fields.Many2one('account.account', string='Credit Account', domain="[('user_type_id.type', '=', 'liquidity')]")

    journal_id = fields.Many2one('account.journal', string='Journal',
        check_company=True, 
        default=_get_default_journal)
    
    payment_line = fields.One2many('payment.amount.line.approval','appr_id')

    def action_create_account_move(self):
        """ Create journal entry. """
        self.ensure_one()
        approval_req_rec = self.env['approval.request'].browse(self._context.get('active_id'))
        
        line_ids = []
        
        if approval_req_rec.has_amount_lines:
            for item in approval_req_rec.amounts_ids:
                line_ids.append((0, 0, {'name': item.name, 'account_id':item.account_id.id, 'debit':item.amount, 'currency_id': approval_req_rec.currency_id.id}))
        else:
            line_ids.append((0, 0, {'name':approval_req_rec.name, 'account_id':approval_req_rec.account_id.id, 'debit':approval_req_rec.amount, 'currency_id': approval_req_rec.currency_id.id}))
        
#         move_id = self.env['account.move'].create({})


        for line in self.payment_line:
            line_ids.append((0, 0, {'name':line.name, 'account_id':line.account_id.id, 'credit':line.amount, 'currency_id': approval_req_rec.currency_id.id}))
        move_id = self.env['account.move'].with_context(default_move_type='entry').create({'journal_id': self.journal_id.id, 'currency_id': approval_req_rec.currency_id.id, 'ref':approval_req_rec.name,
                'isn_approval_id':approval_req_rec.id,'line_ids': line_ids}) 
        move_id.action_post()
        
        approval_req_rec.account_move_id = move_id.id
        approval_req_rec.move_id_created = True
        domain = [
            ('res_model', '=', 'approval.request'),
            ('res_id', 'in', approval_req_rec.ids),
            ('activity_type_id', '=', self.env.ref('isn_approval_custom.mail_activity_pay_process').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Journal Entry Created")

        if approval_req_rec.approval_type == 'direct_procurement':
            store_officer_ids = approval_req_rec.branch_id.store_user_ids
            for user in store_officer_ids: 
                approval_req_rec.activity_schedule('isn_approval_custom.mail_activity_approval_release_products', user_id=user.id)
        
        
class PaymentAmountLineApproval(models.TransientModel):
    _name = 'payment.amount.line.approval'
    
    appr_id = fields.Many2one('payment.approval.entry', required=True, ondelete='cascade')
    name = fields.Char('Description', required=True)
    account_id = fields.Many2one('account.account', string='Credit Account', domain="['|',('user_type_id.type', '=', 'liquidity'), ('name', 'ilike','Outstanding Payments')]", required=True)
    amount = fields.Float(string="Amount", required=True)
        
        
        
        
        
        
        
        
        

# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class AccountPayment(models.Model):
    _inherit = "account.payment"

    show_confirm_button = fields.Boolean(string="Show Confirm Button" ,compute='_compute_show_confirm_btn')

    def _compute_show_confirm_btn(self):
        current_user = self.env.user
        user_ids = [self.env.company.hoa_authorizer.id]
        for rec in self:
            if current_user.has_group("base.user_admin") and rec.state == 'draft':
                rec.show_confirm_button = True
            elif user_ids and current_user.id in user_ids and rec.state == 'draft':
                rec.show_confirm_button = True
            else:
                rec.show_confirm_button = False


    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        user_ids = self.env.company.hoa_authorizer
        for user in user_ids:
            domain = [
                ('res_model', '=', 'account.payment'),
                ('res_id', 'in', self.ids),
                ('user_id', 'in', user.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_authorize_payment').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                res.activity_schedule('ag_field_service.mail_activity_authorize_payment', user_id=user.id)
        return res 

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for payment in self:       
            domain = [
                ('res_model', '=', 'account.payment'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_authorize_payment').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Entry got Authorized")
            if payment.payment_type == 'inbound':
                deposit_history_id = self.env['deposit.history'].sudo().search([('payment_id', '=', payment.id)])
                if not deposit_history_id:
                    deposit_history_id = self.env['deposit.history'].create({
                            'partner_id': payment.partner_id.id,
                            'payment_id': payment.id,
                            'date': payment.date,
                            'deposit_amount': payment.amount,
                            'ref': payment.ref,
                            'journal_id': payment.journal_id.id,
                        })
                else:
                    deposit_history_id = self.env['deposit.history'].update({
                            'partner_id': payment.partner_id.id,
                            'date': payment.date,
                            'deposit_amount': payment.amount,
                            'ref': payment.ref,
                            'journal_id': payment.journal_id.id,
                        })
            # elif payment.payment_type == 'outbound':
            #     expense_history_id = self.env['expense.history'].sudo().search([('payment_id', '=', payment.id)])
            #     if not expense_history_id:
            #         expense_history_id = self.env['expense.history'].create({
            #             'partner_id': payment.partner_id.id,
            #             'payment_id': payment.id,
            #             'date': payment.date,
            #             'expense_amount': payment.amount,
            #             'ref': payment.ref,
            #             'journal_id': payment.journal_id.id,
            #         })
            #     else:
            #         expense_history_id = self.env['expense.history'].update({
            #             'partner_id': payment.partner_id.id,
            #             'date': payment.date,
            #             'expense_amount': payment.amount,
            #             'ref': payment.ref,
            #             'journal_id': payment.journal_id.id,
            #         })
        return res
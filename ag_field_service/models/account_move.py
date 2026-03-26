# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime, timedelta

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_approver_ids(self):
        vals = []
        head_of_account = self.env.company.head_of_account.id
        general_manager_id = self.env.company.general_manager_id.id
        if head_of_account != general_manager_id:
            vals.append((0,0, {'user_id': self.env.company.head_of_account.id,'status': 'new'}))
            vals.append((0,0, {'user_id': self.env.company.general_manager_id.id,'status': 'new'}))
        else:
            vals.append((0,0, {'user_id': self.env.company.head_of_account.id,'status': 'new'}))
        return vals


    @api.model
    def _read_group_request_status(self, stages, domain, order):
        request_status_list = dict(self._fields['request_status'].selection).keys()
        return request_status_list

    approver_ids = fields.One2many('vendorbill.approver', 'move_id', string="Approvers", check_company=True, readonly=True, default=_get_default_approver_ids)
    show_confirm_button = fields.Boolean(string="Show Confirm Button" ,compute='_compute_show_confirm_btn')
    show_register_payment_button = fields.Boolean(string="Show Confirm Button" ,compute='_compute_register_payment_button')

    @api.depends('company_id.general_manager_id', 'company_id.head_of_account', 'company_id.hoa_authorizer', 'state')
    def _compute_show_confirm_btn(self):
        current_user = self.env.user
        user_ids = [self.env.company.hoa_authorizer.id]
        for account in self:
            if current_user.has_group("base.user_admin") and account.state == 'draft':
                account.show_confirm_button = True
            elif account.move_type == 'out_invoice' and account.state == 'draft':
                account.show_confirm_button = True
            elif user_ids and current_user.id in user_ids and (account.state == 'draft' or account.move_type != 'entry'):
                account.show_confirm_button = True
            else:
                account.show_confirm_button = False

    def _compute_register_payment_button(self):
        current_user = self.env.user
        user_ids = self.env.company.account_payable_user_ids.ids
        for rec in self:
            if current_user.has_group("base.user_admin") and (rec.request_status == 'approved' or rec.state == 'posted') and rec.payment_state in ['not_paid', 'partial'] and rec.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt']:
                rec.show_register_payment_button = True
            elif (rec.request_status == 'approved' or rec.state == 'posted') and rec.payment_state in ['not_paid', 'partial'] and rec.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'] and current_user.id in user_ids:
                rec.show_register_payment_button = True
            else:
                rec.show_register_payment_button = False

    request_status = fields.Selection([
        ('new', 'Pending'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel'),
    ], default="new", compute="_compute_request_status", string="Approval Status",
        store=True,
        group_expand='_read_group_request_status')
    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancel')], compute="_compute_user_status")
    
    reapprove_request = fields.Boolean('Reapprove Request', readonly=True)
    
    
    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for move in self:
            approver_ids = move.approver_ids.filtered(lambda approver: approver.user_id == self.env.user)
            if approver_ids:
                move.user_status = approver_ids[0].status
            else:
                move.user_status = approver_ids.status

    @api.depends('approver_ids.status')
    def _compute_request_status(self):
        for move in self:
            if move.move_type == 'in_invoice':
                status_lst = move.mapped('approver_ids.status')
                minimal_approver =  len(status_lst)
                if status_lst:
                    if status_lst.count('cancel'):
                        status = 'cancel'
                    elif status_lst.count('refused'):
                        status = 'refused'
                    elif status_lst.count('new'):
                        status = 'new'
                    elif status_lst.count('approved') >= minimal_approver:
                        status = 'approved'
                    else:
                        status = 'pending'
                else:
                    status = 'new'
            else:
                status = 'approved'
            move.request_status = status
            
    @api.model
    def create(self, vals):
        if 'invoice_date' not in vals:
            vals.update({
                            'invoice_date':datetime.now().date()
                        })
        res = super(AccountMove, self).create(vals)
        if res.move_type == 'in_invoice':
            user_ids = self.env.company.hoa_authorizer
            for user in user_ids:
                domain = [
                    ('res_model', '=', 'account.move'),
                    ('res_id', 'in', self.ids),
                    ('user_id', 'in', user.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_validate_vendor_bill').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    res.activity_schedule('ag_field_service.mail_activity_validate_vendor_bill', user_id=user.id)
        return res 


    @api.constrains('date', 'invoice_date')
    def _check_date(self):
        for rec in self:
            if rec.invoice_date and rec.invoice_date < rec.date:
                raise ValidationError("Bill Date cannot be earlier than Accounting Date !")

    # @api.model_create_multi
    # def create(self, vals_list):
    #     # OVERRIDE
    #     rslt = super(AccountMove, self).create(vals_list)
    #     for r in rslt:
    #         if r.move_type == 'in_invoice':
    #             for rep in r.acc_dep_rep:
    #                 r.activity_schedule('isn_vendor_bill_approval.mail_activity_bill_validate',summary='Validate the Bill',
    #                                         user_id=rep.id)
    #     return rslt
            
    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        if self.move_type == 'in_invoice':
            domain = [
                ('res_model', '=', 'account.move'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_validate_vendor_bill').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Bill Cancelled")
                
            view = 'Vendor Bill'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
            
            
            body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
            body_dynamic_html += '<p> Vendor Bill: %s, you created is Cancelled by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Vendor Bill: [%s] Cancelled'% self.name,
                'body_html': body_dynamic_html,
                'email_to': self.create_uid.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
        return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.invoice_line_ids.purchase_order_id and self.cost_category_id:
            purchase_order_id = self.invoice_line_ids.purchase_order_id
            cost_entry_id = self.env['cost.entry'].sudo().search([('purchase_id', '=', purchase_order_id.id), ('branch_id', '=', self.branch_id.id)])
            if not cost_entry_id:
                cost_entry_id = self.env['cost.entry'].create({
                        'partner_id': self.partner_id.id,
                        'currency_id': self.currency_id.id,
                        'cost_category_id': self.cost_category_id.id,
                        'amount': self.amount_total,
                        'effective_date': purchase_order_id.effective_date or datetime.now(),
                        'purchase_id': purchase_order_id.id,
                        'branch_id': self.branch_id.id
                    })
        if self.move_type == 'in_invoice':
            domain = [
                ('res_model', '=', 'account.move'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_validate_vendor_bill').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Vendor Bill Validated")
            approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
            if approvers:
                approvers = approvers[0]
            approvers._create_activity()
            approvers.write({'status': 'pending'})
        return res
            
    # def action_post(self):
    #     res = super(AccountMove, self).action_post()
    #     if self.move_type == 'in_invoice':
    #         domain = [
    #             ('res_model', '=', 'account.move'),
    #             ('res_id', 'in', self.ids),
    #             ('activity_type_id', '=', self.env.ref('isn_vendor_bill_approval.mail_activity_bill_validate').id),
    #         ]
    #         activities = self.env['mail.activity'].sudo().search(domain)
    #         if activities:
    #             activities.sudo().action_feedback(feedback="Bill Validated")
            
    #         approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
    #         if approvers:
    #             approvers = approvers[0]
    #         approvers._create_activity()
    #         approvers.write({'status': 'pending'})
    #     return res
            
    def _get_user_approval_activities(self, user):
        domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_bill_approval').id),
            ('user_id', '=', user.id)
        ]
        activities = self.env['mail.activity'].search(domain)
        return activities
            
    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})
        
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        if approvers:
            approvers = approvers[0]
        approvers._create_activity()
        approvers.write({'status': 'pending'})
        
        
        status_lst = self.mapped('approver_ids.status')
        minimal_approver =  len(status_lst)
        if (status_lst.count('approved')) >= minimal_approver:
            
            
            view = 'Vendor Bill'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
            
            
            body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
            body_dynamic_html += '<p> Your Request to approve Vendor Bill: %s, is Approved by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Vendor Bill: [%s] Approved'% self.name,
                'body_html': body_dynamic_html,
                'email_to': self.create_uid.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
            
            
            for user in self.env.company.account_payable_user_ids:
                self.activity_schedule('ag_field_service.mail_activity_bill_reg_payment',summary='Process the Payment',
                                        user_id=user.id)
        
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback(feedback="Bill Approved")



    def action_reapprove(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved'})
        self.reapprove_request = False
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        if approvers:
            approvers = approvers[0]
        approvers._create_activity()
        approvers.write({'status': 'pending'})
        
        
        status_lst = self.mapped('approver_ids.status')
        minimal_approver =  len(status_lst)
        if (status_lst.count('approved')) >= minimal_approver:
            view = 'Vendor Bill'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
            
            
            body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
            body_dynamic_html += '<p> Your Request to approve Vendor Bill: %s, is Approved by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Vendor Bill: [%s] Approved'% self.name,
                'body_html': body_dynamic_html,
                'email_to': self.create_uid.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
            
            
            for rep in self.env.company.account_payable_user_ids:
                self.activity_schedule('ag_field_service.mail_activity_bill_reg_payment',summary='Process the Payment',
                                        user_id=rep.id)
        else:
            view = 'Vendor Bill'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
            
            
            body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
            body_dynamic_html += '<p> Your Request to reapprove Vendor Bill: %s, is Reapproved by: %s. And waiting for final Approval </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Vendor Bill: [%s] Reapproved. Waiting final Approval'% self.name,
                'body_html': body_dynamic_html,
                'email_to': self.create_uid.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
        
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback(feedback="Bill Reapproved")



    def action_refuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})
        
        view = 'Vendor Bill'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
        
        
        body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
        body_dynamic_html += '<p> Your Request to approve Vendor Bill: %s, is Refused by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name

        body_dynamic_html += '<div style = "margin: 16px;">\
                                    <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                     color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                     margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                     cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                     border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
            link, view)
        
        
        
        
        vals = {
            'subject': 'Vendor Bill: [%s] Refused'% self.name,
            'body_html': body_dynamic_html,
            'email_to': self.create_uid.email_formatted,
            'auto_delete': False,
            'email_from': self.env.user.email_formatted,
        }
        
        mail_id = self.env['mail.mail'].sudo().create(vals)
        mail_id.sudo().send()            
        
        
        
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback(feedback="Bill Refused")
        
        
    def action_rerefuse(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'refused'})
        self.reapprove_request = False
        
        view = 'Vendor Bill'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=account.move' % self.id
        
        
        body_dynamic_html = '<p>Dear %s </p>' % self.create_uid.name
        body_dynamic_html += '<p> Your Request to reapprove Vendor Bill: %s, is Refused by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name

        body_dynamic_html += '<div style = "margin: 16px;">\
                                    <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                     color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                     margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                     cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                     border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
            link, view)
        
        
        
        
        vals = {
            'subject': 'Vendor Bill: [%s], Reapproval request Refused'% self.name,
            'body_html': body_dynamic_html,
            'email_to': self.create_uid.email_formatted,
            'auto_delete': False,
            'email_from': self.env.user.email_formatted,
        }
        
        mail_id = self.env['mail.mail'].sudo().create(vals)
        mail_id.sudo().send()            
        
        
        
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback(feedback="Bill Refused")
        
        
        
        
    def action_register_payment(self):
        if self.filtered(lambda move: move.request_status != 'approved'):
            raise UserError(_('Approve the Bill first, Contact Admin'))
        res = super(AccountMove, self).action_register_payment()
        return res
        
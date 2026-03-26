# -*- coding: utf-8 -*-

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    @api.model
    def _get_default_journal(self):
        domain = [('company_id', '=', self.env.company.id), ('type', 'in', ['general'])]
        journal = self.env['account.journal'].search(domain, limit=1)
        return journal    
    
    @api.model
    def _get_default_currency(self):
        journal = self._get_default_journal()
        return journal.currency_id or journal.company_id.currency_id

    def _get_default_branch(self):
        branch = False
        if len(self.env.user.branch_ids) == 1:
            branch = self.env.user.branch_id
            return branch

    def _get_branch_domain(self):
        """methode to get branch domain"""
        company = self.env.company
        branch_ids = self.env.user.branch_ids
        branch = branch_ids.filtered(
            lambda branch: branch.company_id == company)
        return [('id', 'in', branch.ids)]

    branch_id = fields.Many2one('res.branch', string='Country Region', store=True,
                                readonly=False,
                                default=_get_default_branch,
                                domain=_get_branch_domain)
 
    currency_id = fields.Many2one('res.currency',
        string='Currency',
        default=_get_default_currency)
    account_move_id = fields.Many2one('account.move')
    move_id_created = fields.Boolean(string='Journal Created')
    picking_id_created = fields.Boolean(string='Picking Created')
    date = fields.Datetime(string="Date",default=fields.Datetime.now, readonly=True)
    approver_ids = fields.One2many('approval.approver', 'request_id', string="Approvers", check_company=True, readonly=True)
    account_id = fields.Many2one('account.account',string='Account', domain="[('id','in',account_ids)]")
    department_id = fields.Many2one('hr.department', compute='_compute_department_id', store=True)
    account_ids = fields.Many2many(related='department_id.account_ids')
    amounts_ids = fields.One2many('approval.amount.line','approval_id')
    has_amount_lines = fields.Boolean('Has Amount Lines', default=True)
    acc_dep_rep = fields.Many2many(
                       'res.users','acc_dep_rep_rel','process_acc_dep_rep','process_acc_rep_ref', string='Accounts Department Rep',
                        domain=lambda self: [('groups_id', 'in', self.env.ref('account.group_account_user').id)])
    # approval_subject = fields.Char("Approval Subject", required=True)
    request_owner_id = fields.Many2one('res.users', string="Request Owner", readonly=True, required=True,
        check_company=True, domain="[('company_ids', 'in', company_id)]")
    category_id = fields.Many2one('approval.category', string="Category", required=True, readonly=True)
    
    reapprove_request = fields.Boolean('Reapprove Request', readonly=True)

    payee_details = fields.Text("Payee Details")
    approval_type = fields.Selection([('purchase', 'RFQ Need Application'),
                                        ('payment','Payment Application'),
                                        ('direct_procurement','Direct Procurement Application')], string="Approval Type")
    location = fields.Many2one("region.location", string="Location")
    # attachment_ids = fields.Many2many('ir.attachment', string="Attachments", copy=False)
    nonsku_product_line_ids = fields.One2many("approval.nonsku.product.line", "approval_request_id", string="Non-SKU Product Lines")
    total_amount = fields.Monetary("SKU Total Amount", compute="_compute_total_amount", store=True)
    nonsku_total_amount = fields.Monetary("Non-SKU Total Amount", compute="_compute_total_amount", store=True)
    overall_total_amount = fields.Monetary("Total Amount", compute="_compute_total_amount", store=True)
    show_create_rfq = fields.Boolean("Show Create RFQ", compute="_compute_show_create_rfq")

    def _compute_show_create_rfq(self):
        procurement_user_ids = self.env.company.procurement_user_ids.ids
        # procurement_manager_id = self.env.company.procurement_manager_id
        # procurement_user_ids.extend(procurement_manager_id.ids)
        current_user = self.env.user
        for rec in self:
            rec.show_create_rfq = False
            if current_user.id in procurement_user_ids:
                if rec.approval_type == 'purchase' and rec.request_status == 'approved' and rec.purchase_order_count <= 0:
                    if not rec.nonsku_product_line_ids:
                        rec.show_create_rfq = True
                    if rec.nonsku_product_line_ids and all(line.is_product_created for line in rec.nonsku_product_line_ids):
                        domain = [
                            ('res_model', '=', 'approval.request'),
                            ('res_id', 'in', rec.ids),
                            ('activity_type_id', '=', self.env.ref('isn_approval_custom.mail_activity_create_nonsku_products').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            activities.sudo().action_feedback(feedback="Non-SKU Items Created")
                        for procurement_user_id in procurement_user_ids:
                            domain = [
                                ('res_model', '=', 'approval.request'),
                                ('res_id', 'in', rec.ids),
                                ('activity_type_id', '=', self.env.ref('isn_approval_custom.mail_activity_create_rfq').id),
                                ('user_id', '=', procurement_user_id),
                            ]
                            activities = self.env['mail.activity'].sudo().search(domain)
                            if not activities:
                                rec.activity_schedule('isn_approval_custom.mail_activity_create_rfq', user_id=procurement_user_id)
                        rec.show_create_rfq = True

    @api.depends('product_line_ids', 'product_line_ids.amount', 'nonsku_product_line_ids', 'nonsku_product_line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.product_line_ids.mapped('amount'))
            rec.nonsku_total_amount = sum(rec.nonsku_product_line_ids.mapped('amount'))
            if self.category_id.approval_type != 'payment':
                rec.amount = sum(rec.product_line_ids.mapped('amount'))
            rec.overall_total_amount = rec.total_amount + rec.nonsku_total_amount

    def action_approve(self, approver=None):
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=approval.request' % self.id
        view = 'Approval Request'
        
        
        belw_approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'approved')
        for apprvr in belw_approvers:
            
            
            
            body_dynamic_html = '<p>Dear %s </p>' % apprvr.user_id.name
            body_dynamic_html += '<p> Approval Request you approved: %s, is Approved by: %s. </p>' % (self.name, self.env.user.name)
    #             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Approval Request: [%s] Follow up [Approval]'% self.name,
                'body_html': body_dynamic_html,
                'email_to': apprvr.user_id.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
            
            
        res = super(ApprovalRequest,self).action_approve(approver)
        self.reapprove_request = False
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        if approvers:
            approvers = approvers[0]
        approvers._create_activity()
        approvers.write({'status': 'pending'})
        status_lst = self.mapped('approver_ids.status')
        minimal_approver = self.approval_minimum if len(status_lst) >= self.approval_minimum else len(status_lst)
        if (status_lst.count('approved')) >= minimal_approver:
            
            
            
            body_dynamic_html = '<p>Dear %s </p>' % self.request_owner_id.name
            body_dynamic_html += '<p> Your Request to Approve: %s, is Approved by: %s. </p>' % (self.name, self.env.user.name)
    #             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Approval Request: [%s] Approved'% self.name,
                'body_html': body_dynamic_html,
                'email_to': self.create_uid.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()
            if self.approval_type == 'purchase':
                procurement_user_ids = self.company_id.procurement_user_ids
                for procurement_user_id in procurement_user_ids:
                    if self.nonsku_product_line_ids:
                        self.activity_schedule('isn_approval_custom.mail_activity_create_nonsku_products', user_id=procurement_user_id.id)
                    else:    
                        self.activity_schedule('isn_approval_custom.mail_activity_create_rfq', user_id=procurement_user_id.id)              
            
            if self.approval_type == 'payment':
                for rep in self.acc_dep_rep:
                    self.activity_schedule('isn_approval_custom.mail_activity_pay_process',
                                            user_id=rep.id)
        return res
    
    
    def action_refuse(self, approver=None):
        
        view = 'Approval Request'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link = base_url + '/web#id=%s&view_type=form&model=approval.request' % self.id
        
        belw_approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'approved')
        for apprvr in belw_approvers:
            
            body_dynamic_html = '<p>Dear %s </p>' % apprvr.user_id.name
            body_dynamic_html += '<p> Approval Request you approved: %s, is Refused by: %s. </p>' % (self.name, self.env.user.name)
    #             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name
    
            body_dynamic_html += '<div style = "margin: 16px;">\
                                        <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                         color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                         margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                         cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                         border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
                link, view)
            
            
            
            
            vals = {
                'subject': 'Approval Request: [%s] Follow up [Refusal]'% self.name,
                'body_html': body_dynamic_html,
                'email_to': apprvr.user_id.email_formatted,
                'auto_delete': False,
                'email_from': self.env.user.email_formatted,
            }
            
            mail_id = self.env['mail.mail'].sudo().create(vals)
            mail_id.sudo().send()            
        
        
        
        res = super(ApprovalRequest,self).action_refuse(approver)
        
        body_dynamic_html = '<p>Dear %s </p>' % self.request_owner_id.name
        body_dynamic_html += '<p> Your Request to Approval: %s, is Refused by: %s. </p>' % (self.name, self.env.user.name)
#             body_dynamic_html += '<p> Approver: %s </p>' % self.env.user.name

        body_dynamic_html += '<div style = "margin: 16px;">\
                                    <a href=%s style = "padding: 5px 10px; font-size: 12px; line-height: 18px;\
                                     color: #FFFFFF; border-color:#875A7B; text-decoration: none; display: inline-block; \
                                     margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; \
                                     cursor: pointer; white-space: nowrap; background-image: none; background-color: #875A7B;\
                                     border: 1px solid #875A7B; border-radius:3px">View %s</a></div><p> Thank You.</div>' % (
            link, view)
        
        
        
        
        vals = {
            'subject': 'Approval Request: [%s] Refused'% self.name,
            'body_html': body_dynamic_html,
            'email_to': self.create_uid.email_formatted,
            'auto_delete': False,
            'email_from': self.env.user.email_formatted,
        }
        
        mail_id = self.env['mail.mail'].sudo().create(vals)
        mail_id.sudo().send()            
        return res
    
    
#     @api.onchange('category_id', 'request_owner_id')
#     def _onchange_category_id(self):
#         res = super(ApprovalRequest, self)._onchange_category_id()
#         if self.category_id.approval_type == 'payment':
#             self.acc_dep_rep = self.category_id.to_process_payment_user_id
#         return res

    @api.depends('category_id', 'request_owner_id')
    def _compute_approver_ids(self):
        for request in self:
            #Don't remove manually added approvers
            users_to_approver = defaultdict(lambda: self.env['approval.approver'])
            for approver in request.approver_ids:
                users_to_approver[approver.user_id.id] |= approver
            users_to_category_approver = defaultdict(lambda: self.env['approval.category.approver'])
            for approver in request.category_id.approver_ids:
                users_to_category_approver[approver.user_id.id] |= approver
            new_users = False
            manager_user = 0
            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee.parent_id.user_id:
                    new_users = employee.parent_id.user_id
                    manager_user = employee.parent_id.user_id.id
            if new_users:
                new_users |= request.category_id.user_ids
            else:
                new_users = request.category_id.user_ids
            approver_id_vals = []
            for user in new_users:
                # Force require on the manager if he is explicitely in the list
                required = users_to_category_approver[user.id].required or \
                    (request.category_id.manager_approval == 'required' if manager_user == user.id else False)
                current_approver = users_to_approver[user.id]
                if current_approver and current_approver.required != required:
                    approver_id_vals.append(Command.update(current_approver.id, {'required': required}))
                elif not current_approver:
                    approver_id_vals.append(Command.create({
                        'user_id': user.id,
                        'status': 'new',
                        'required': required,
                    }))
            request.update({'approver_ids': approver_id_vals})
    
    
    
    @api.onchange('category_id', 'request_owner_id', 'approval_type', 'location')
    def _onchange_category_id(self):
        if self.category_id.approval_type == 'payment' and self.location:
            self.acc_dep_rep = [(6,0, self.location.account_rep_id.ids)] #self.category_id.to_process_payment_user_id
        current_users = self.approver_ids.mapped('user_id')
        # print("current_users****************", current_users.mapped('name'))
        new_users = False
        if self.category_id.manager_approval:
            employee = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if employee.parent_id.user_id:
                new_users = employee.parent_id.user_id
        if new_users:
            new_users |= self.category_id.user_ids
        else:
            new_users = self.category_id.user_ids
        for user in new_users - current_users:
            self.approver_ids += self.env['approval.approver'].new({
                'user_id': user.id,
                'request_id': self.id,
                'status': 'new'})
    
    
    
    @api.depends('approver_ids.status')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)
            if status_lst:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('new') == len(status_lst):
                    status = 'new'
                elif status_lst.count('approved') >= minimal_approver:
                    status = 'approved'
                else:
                    status = 'pending'
            else:
                status = 'new'
            request.request_status = status
    
    
    # @api.constrains('has_amount_lines', 'amount','amounts_ids')
    # def _check_amount_line_total(self):
    #     for rec in self:
            
    #         if rec.has_amount_lines:
    #             total = 0
    #             for line in rec.amounts_ids:
    #                 total += line.amount
    #             if rec.amount != total:
    #                 raise ValidationError(_("Please Enter Total Amount correctly. which is =  %s")%total)
    
    
    @api.depends('request_owner_id')
    def _compute_department_id(self):
        for rec in self:
            emp = self.env['hr.employee'].search([('user_id', '=',rec.request_owner_id.id)], limit=1)
            if emp:
                rec.department_id = emp.department_id.id
            else:
                rec.department_id = None
            

    def action_view_move(self):
        move_id = self.account_move_id
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        form_view = [(self.env.ref('account.view_move_form').id, 'form')]
        action['views'] = form_view
        action['res_id'] = move_id.id
        context = {'default_move_type': 'entry', 'search_default_misc_filter':1, 'view_no_maturity': True}
        action['context'] = context
        return action

#     def action_confirm(self):
#         for request in self:
#             if request.approval_type == 'payment' and request.has_amount_lines  and not request.amounts_ids:
#                 raise UserError(_("You cannot create an empty payment request."))
#         return super().action_confirm()


    def action_confirm(self):
        if self.approval_type == 'payment' and self.amount <= 0:
            raise ValidationError("Payment Approval request cannot submit with amount 0 !")
        if len(self.approver_ids) < self.approval_minimum:
            raise UserError(_("You have to add at least %s approvers to confirm your request.", self.approval_minimum))
        if self.requirer_document == 'required' and not self.attachment_number:
            raise UserError(_("You have to attach at lease one document."))
        for request in self:
            if request.approval_type == 'payment' and request.has_amount_lines  and not request.amounts_ids:
                raise UserError(_("You cannot create an empty payment request."))
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        if approvers:
            approvers = approvers[0]
        approvers._create_activity()
        approvers.write({'status': 'pending'})
        self.write({'date_confirmed': fields.Datetime.now()})

    def action_create_purchase_orders(self):
        """ Create and/or modifier Purchase Orders. """
        self.ensure_one()
        new_purchase_order = False
        if self.product_line_ids:
            self.product_line_ids._check_products_vendor()
            for line in self.product_line_ids:
                seller = line._get_seller_id()
                vendor = seller.name
                po_domain = line._get_purchase_orders_domain(vendor)
                purchase_orders = self.env['purchase.order'].search(po_domain)

                if purchase_orders:
                    # Existing RFQ found: check if we must modify an existing
                    # purchase order line or create a new one.
                    purchase_line = self.env['purchase.order.line'].search([
                        ('order_id', 'in', purchase_orders.ids),
                        ('product_id', '=', line.product_id.id),
                        ('product_uom', '=', line.product_id.uom_po_id.id),
                    ], limit=1)
                    purchase_order = self.env['purchase.order']
                    if purchase_line:
                        # Compatible po line found, only update the quantity.
                        line.purchase_order_line_id = purchase_line.id
                        purchase_line.product_qty += line.po_uom_qty
                        purchase_order = purchase_line.order_id
                    else:
                        # No purchase order line found, create one.
                        purchase_order = purchase_orders[0]
                        po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                            line.product_id,
                            line.quantity,
                            line.product_uom_id,
                            line.company_id,
                            seller,
                            purchase_order,
                        )
                        new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                        line.purchase_order_line_id = new_po_line.id
                        purchase_order.order_line = [(4, new_po_line.id)]

                    # Add the request name on the purchase order `origin` field.
                    new_origin = set([self.name])
                    if purchase_order.origin:
                        missing_origin = new_origin - set(purchase_order.origin.split(', '))
                        if missing_origin:
                            purchase_order.write({'origin': purchase_order.origin + ', ' + ', '.join(missing_origin)})
                    else:
                        purchase_order.write({'origin': ', '.join(new_origin)})
                    new_purchase_order = purchase_order
                else:
                    # No RFQ found: create a new one.
                    po_vals = line._get_purchase_order_values(vendor)
                    new_purchase_order = self.env['purchase.order'].create(po_vals)
                    po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                        line.product_id,
                        line.quantity,
                        line.product_uom_id,
                        line.company_id,
                        seller,
                        new_purchase_order,
                    )
                    
                    new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                    new_po_line.update({
                            'price_unit': line.price_unit,
                        })
                    line.purchase_order_line_id = new_po_line.id
                    new_purchase_order.order_line = [(4, new_po_line.id)]
                new_purchase_order.currency_id = self.currency_id.id
                new_purchase_order.location = self.location.id
                new_purchase_order.department_id = self.department_id.id
        if self.nonsku_product_line_ids:
            self.nonsku_product_line_ids._check_products_vendor()
            for line in self.nonsku_product_line_ids:
                seller = line._get_seller_id()
                vendor = seller.name
                po_domain = line._get_purchase_orders_domain(vendor)
                purchase_orders = self.env['purchase.order'].search(po_domain)

                if purchase_orders:
                    # Existing RFQ found: check if we must modify an existing
                    # purchase order line or create a new one.
                    purchase_line = self.env['purchase.order.line'].search([
                        ('order_id', 'in', purchase_orders.ids),
                        ('product_id', '=', line.product_product_id.id),
                        ('product_uom', '=', line.product_product_id.uom_po_id.id),
                    ], limit=1)
                    purchase_order = self.env['purchase.order']
                    if purchase_line:
                        # Compatible po line found, only update the quantity.
                        line.purchase_order_line_id = purchase_line.id
                        purchase_line.product_qty += line.po_uom_qty
                        purchase_order = purchase_line.order_id
                    else:
                        # No purchase order line found, create one.
                        purchase_order = purchase_orders[0]
                        po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                            line.product_product_id,
                            line.quantity,
                            line.product_uom,
                            line.company_id,
                            seller,
                            purchase_order,
                        )
                        new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                        new_po_line.update({
                            'price_unit': line.price_unit,
                        })
                        line.purchase_order_line_id = new_po_line.id
                        purchase_order.order_line = [(4, new_po_line.id)]

                    # Add the request name on the purchase order `origin` field.
                    new_origin = set([self.name])
                    if purchase_order.origin:
                        missing_origin = new_origin - set(purchase_order.origin.split(', '))
                        if missing_origin:
                            purchase_order.write({'origin': purchase_order.origin + ', ' + ', '.join(missing_origin)})
                    else:
                        purchase_order.write({'origin': ', '.join(new_origin)})
                    new_purchase_order = purchase_order
                else:
                    # No RFQ found: create a new one.
                    po_vals = line._get_purchase_order_values(vendor)
                    new_purchase_order = self.env['purchase.order'].create(po_vals)
                    po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                        line.product_product_id,
                        line.quantity,
                        line.product_uom,
                        line.company_id,
                        seller,
                        new_purchase_order,
                    )
                    
                    new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                    new_po_line.update({
                            'price_unit': line.price_unit,
                        })
                    line.purchase_order_line_id = new_po_line.id
                    new_purchase_order.order_line = [(4, new_po_line.id)]
                new_purchase_order.currency_id = self.currency_id.id
                new_purchase_order.location = self.location.id
                new_purchase_order.department_id = self.department_id.id
        domain = [
            ('res_model', '=', 'approval.request'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('isn_approval_custom.mail_activity_create_rfq').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="RFQ Created")

        purchase_ids = self.product_line_ids.purchase_order_line_id.order_id.ids
        purchase_ids.extend(self.nonsku_product_line_ids.purchase_order_line_id.order_id.ids)
        if len(purchase_ids) > 1:
            domain = [('id', 'in', purchase_ids)]
            return {
                'name': _('Purchase Orders'),
                'view_type': 'tree',
                'view_mode': 'list,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'domain': domain,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Request for Quotation'),
                'res_model': 'purchase.order',
                'res_id': new_purchase_order.id,
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,
                'context': {
                    'quotation_only': True
                }
            }

    def action_release_products(self):
        warehouse_id = self.env['stock.warehouse'].sudo().search([('branch_id', '=', self.branch_id.id)], limit=1)
        location_id = self.env['stock.location'].sudo().search([('usage', '=', 'customer')], limit=1)
        if warehouse_id:
            move_line = []
            for line in self.product_line_ids:
                vals = {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'name': line.product_id.name,
                    'location_id': warehouse_id.lot_stock_id.id,
                    'location_dest_id': location_id.id,
                }
                move_line.append((0, 0, vals))
            picking_id = self.env['stock.picking'].create({
                    'partner_id': self.partner_id.id,
                    'picking_type_id': warehouse_id.out_type_id.id,
                    'location_id': warehouse_id.lot_stock_id.id,
                    'location_dest_id': location_id.id,
                    'origin': self.name,
                    'move_ids_without_package': move_line,
                    'approval_request_id': self.id,
                })
            picking_id.action_confirm()
            picking_id.move_lines._set_quantities_to_reservation()
            picking_id.with_context(skip_immediate=True).button_validate()
            self.picking_id_created = True
            domain = [
                ('res_model', '=', 'approval.request'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_approval_release_products').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Product Released")

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        for rec in self.product_line_ids:
            conversion_rate = 1
            if rec.product_id and rec.currency_id:
                rate_id =  rec.currency_id.rate_ids.filtered(lambda x: (x.rate
                and x.company_id == (rec.company_id or self.env.company)
                and x.name <= fields.Date.today())).sorted('name')[-1:]
                if rate_id:
                    conversion_rate = rate_id.company_rate
                rec.price_unit = rec.product_id.list_price * conversion_rate

    @api.depends('product_line_ids.purchase_order_line_id', 'nonsku_product_line_ids.purchase_order_line_id')
    def _compute_purchase_order_count(self):
        for request in self:
            purchases = request.product_line_ids.purchase_order_line_id.order_id
            non_sku_purchases = request.nonsku_product_line_ids.purchase_order_line_id.order_id
            request.purchase_order_count = len(purchases) + len(non_sku_purchases)


    def action_open_purchase_orders(self):
        """ Return the list of purchase orders the approval request created or
        affected in quantity. """
        self.ensure_one()
        purchase_ids = self.product_line_ids.purchase_order_line_id.order_id.ids
        purchase_ids.extend(self.nonsku_product_line_ids.purchase_order_line_id.order_id.ids)
        domain = [('id', 'in', purchase_ids)]
        action = {
            'name': _('Purchase Orders'),
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'domain': domain,
        }
        return action


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    currency_id = fields.Many2one('res.currency', related="approval_request_id.currency_id", string="Currency", readonly=True)
    price_unit = fields.Monetary("Unit Price")
    amount = fields.Monetary("Subtotal", compute="_compute_amount", store=True)


    @api.onchange('product_id')
    def onchange_product_id(self):
        conversion_rate = 1
        for rec in self:
            if rec.product_id and rec.currency_id:
                rate_id =  rec.currency_id.rate_ids.filtered(lambda x: (x.rate
                and x.company_id == (rec.company_id or self.env.company)
                and x.name <= fields.Date.today())).sorted('name')[-1:]
                if rate_id:
                    conversion_rate = rate_id.company_rate
                rec.price_unit = rec.product_id.list_price * conversion_rate
    
    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.price_unit

class ApprovalNonskuProductLine(models.Model):
    _name = 'approval.nonsku.product.line'
    _description = "Approval Non-SKU Product Line"

    product_id = fields.Char("Products")
    company_id = fields.Many2one(
        string='Company', related='approval_request_id.company_id',
        store=True, readonly=True, index=True)
    description = fields.Char("Description")
    quantity = fields.Float("Quantity")
    product_uom = fields.Many2one("uom.uom", string="Unit of Measure")
    currency_id = fields.Many2one('res.currency', related="approval_request_id.currency_id", string="Currency", readonly=True)
    price_unit = fields.Monetary("Unit Price")
    amount = fields.Monetary("Subtotal", compute="_compute_amount", store=True)
    approval_request_id = fields.Many2one("approval.request", string="Approval", copy=False)
    show_create_product = fields.Boolean("Show Create Product", compute="_compute_show_create_product")
    is_product_created = fields.Boolean("Is Product Created?", compute="_compute_is_product_created")
    product_product_id = fields.Many2one("product.product", string="Product")
    po_uom_qty = fields.Float(
        "Purchase UoM Quantity", compute='_compute_po_uom_qty',
        help="The quantity converted into the UoM used by the product in Purchase Order.")
    purchase_order_line_id = fields.Many2one('purchase.order.line')

    @api.depends('approval_request_id.approval_type', 'product_uom', 'quantity')
    def _compute_po_uom_qty(self):
        for line in self:
            approval_type = line.approval_request_id.approval_type
            if approval_type == 'purchase' and line.product_product_id and line.quantity:
                uom = line.product_uom or line.product_product_id.uom_id
                line.po_uom_qty = uom._compute_quantity(
                    line.quantity,
                    line.product_product_id.uom_po_id
                )
            else:
                line.po_uom_qty = 0.0

    def _compute_is_product_created(self):
        for rec in self:
            rec.is_product_created = False
            product_id = self.env['product.product'].search([('nonsku_product_line_id', '=', rec.id)], limit=1)
            if product_id:
                rec.is_product_created = True
                rec.product_product_id = product_id.id

    def _compute_show_create_product(self):
        procurement_user_ids = self.env.company.procurement_user_ids.ids
        current_user = self.env.user
        for rec in self:
            rec.show_create_product = False
            if not rec.is_product_created and (current_user.id in procurement_user_ids or current_user.has_group('base.user_admin')):
                rec.show_create_product = True

    
    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.price_unit

    def _get_seller_id(self):
        self.ensure_one()
        res = self.env['product.supplierinfo']
        if self.product_product_id and self.quantity:
            res = self.product_product_id.with_company(self.company_id)._select_seller(
                quantity=self.quantity,
                uom_id=self.product_product_id.uom_po_id,
            )
        return res

    def _check_products_vendor(self):
        """ Raise an error if at least one product requires a seller. """
        product_lines_without_seller = self.filtered(lambda line: not line._get_seller_id())
        if product_lines_without_seller:
            product_names = product_lines_without_seller.product_product_id.mapped('display_name')
            raise UserError(
                _('Please set a vendor on product(s) %s.') % ', '.join(product_names)
            )

    def _get_purchase_orders_domain(self, vendor):
        """ Return a domain to get purchase order(s) where this product line could fit in.

        :return: list of tuple.
        """
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('partner_id', '=', vendor.id),
            ('state', '=', 'draft'),
        ]
        return domain

    def _get_purchase_order_values(self, vendor):
        """ Get some values used to create a purchase order.
        Called in approval.request `action_create_purchase_orders`.

        :param vendor: a res.partner record
        :return: dict of values
        """
        self.ensure_one()
        vals = {
            'origin': self.approval_request_id.name,
            'partner_id': vendor.id,
            'company_id': self.company_id.id,
        }
        return vals

    def action_create_product(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Product'),
            'res_model': 'product.product',
            'view_mode': 'form',
            'context': {
                'default_name': self.product_id,
                'default_sale_ok': True,
                'default_purchase_ok': True,
                'default_uom_id':self.product_uom.id,
                'default_uom_po_id':self.product_uom.id,
                'default_nonsku_product_line_id': self.id,
            },
            'target': 'new',
        }



class ApprovalAmountLine(models.Model):
    _name = 'approval.amount.line'
    _description = 'Approval Amount Line'
    
    approval_id = fields.Many2one('approval.request', required=True, ondelete='cascade')
    name = fields.Char('Description', required=True)
    account_id = fields.Many2one('account.account',string='Account', required=True)
    amount = fields.Float(string="Amount", required=True)
    
    
    
    
    
# class MailActivity(models.Model):
#     _inherit = 'mail.activity'
# 
#     def activity_format(self):
#         result = super(MailActivity, self).activity_format()
#         print(result, "<---------------\n\n\n\n")
#         if result:
#             result[0]['can_write'] = False
# #         activity_type_approval_id = self.env.ref('approvals.mail_activity_data_approval').id
# #         for activity in result:
# #             if activity['activity_type_id'][0] == activity_type_approval_id and \
# #                     activity['res_model'] == 'approval.request':
# #                 request = self.env['approval.request'].browse(activity['res_id'])
# #                 approver = request.approver_ids.filtered(lambda approver: activity['user_id'][0] == approver.user_id.id)
# #                 activity['approver_id'] = approver.id
# #                 activity['approver_status'] = approver.status
#         return result
    
    
    
    
    
    
    
    
    
    
    

# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError, UserError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    project_task_id = fields.Many2one("project.task", string="Job Order", copy=False)
    scope_of_work = fields.Char("Scope of Work", copy=False)
    duration_number = fields.Integer(string="Duration", default=1)
    duration_type = fields.Selection([('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months'),
                                      ('years', 'Years')], string='Duration Unit', default='days')
    penalty_non_compilance = fields.Char("Penalty for Non-Compliance", copy=False)
    warranty_number = fields.Integer(string="Warranty", default=1)
    warranty_type = fields.Selection([('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months'),
                                      ('years', 'Years')], string='Warranty Unit', default='days')
    other_term_conditions = fields.Text("Other Terms & Conditions", copy=False)
    invisible_submit_offer = fields.Boolean("Invisible Submit Offer", default=True, copy=False, compute="_compute_invisible_btn_confirm")
    invisible_approve = fields.Boolean("Invisible Approve", default=True, copy=False, compute="_compute_invisible_approve")
    invisible_btn_confirm = fields.Boolean("Invisible Confirm Button", default=True, copy=False, compute="_compute_invisible_btn_confirm")
    invisible_btn_confirm2 = fields.Boolean("Invisible Confirm Button", default=True, copy=False, compute="_compute_invisible_btn_confirm")
    invisible_button_receive_orders = fields.Boolean("Invisible Receive Order", default=True, copy=False, compute="_compute_invisible_button_receive_orders")
    invisible_button_receive_products = fields.Boolean("Invisible Receive Products", default=True, copy=False, compute="_compute_invisible_button_receive_products")
    is_order_received = fields.Boolean("Is Order Received?", default=False, copy=False)
    is_offer_submitted = fields.Boolean("Is offer Submitted?", default=False, copy=False)
    invisible_create_bill = fields.Boolean("Invisible Create Bill", default=True, copy=False, compute="_compute_invisible_create_bill")

    def _compute_invisible_approve(self):
        general_manager_id = self.env.company.general_manager_id
        current_user = self.env.user
        for rec in self:
            rec.invisible_approve = True
            if rec.state == "to approve" and current_user.id == general_manager_id.id:
                rec.invisible_approve = False

    def _compute_invisible_btn_confirm(self):
        procurement_officer_ids = self.env.company.procurement_user_ids
        procurement_manager_id = self.env.company.procurement_manager_id
        current_user = self.env.user
        for rec in self:
            rec.invisible_submit_offer = True
            rec.invisible_btn_confirm = True
            rec.invisible_btn_confirm2 = True
            if rec.state == "sent" and not rec.is_offer_submitted and current_user.id in procurement_officer_ids.ids:
                rec.invisible_submit_offer = False
            if rec.state == "sent" and rec.is_offer_submitted and current_user.id == procurement_manager_id.id:
                rec.invisible_btn_confirm2 = False

    def _compute_invisible_create_bill(self):
        account_payable_user_ids = self.env.company.account_payable_user_ids
        current_user = self.env.user
        for rec in self:
            rec.invisible_create_bill = True
            if rec.state in ["purchase", "done"] and current_user.id in account_payable_user_ids.ids:
                rec.invisible_create_bill = False

    def _compute_invisible_button_receive_products(self):
        store_officer_id = self.location.store_officer_id
        current_user = self.env.user
        for rec in self:
            rec.invisible_button_receive_products = True
            domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', rec.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_po_supply').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not rec.is_shipped and rec.state in ["purchase", "done"] and current_user.id == store_officer_id.id and any(line.product_id.detailed_type in ['product', 'consu'] for line in rec.order_line) and rec.incoming_picking_count != 0:
                if activities:
                    rec.invisible_button_receive_products = False

    def _compute_invisible_button_receive_orders(self):
        store_officer_id = self.location.store_officer_id
        current_user = self.env.user
        for rec in self:
            rec.invisible_button_receive_orders = True
            domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', rec.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_po_supply').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not rec.is_order_received and rec.state in ["purchase", "done"] and current_user.id == store_officer_id.id and any(line.product_id.detailed_type == 'service' for line in rec.order_line):
                if activities:
                    rec.invisible_button_receive_orders = False
            # print("***********", rec.invisible_button_receive_orders)
            # if not rec.is_order_received and rec.state in ["purchase", "done"] and current_user.id == store_officer_id.id and any(line.product_id.detailed_type == 'product' for line in rec.order_line) and rec.incoming_picking_count == 0:
            #     if activities:
            #         rec.invisible_button_receive_orders = False

    def action_rfq_send(self):
        res = super(PurchaseOrder, self).action_rfq_send()
        procurement_officer_ids = self.env.company.procurement_user_ids
        if procurement_officer_ids:
            for rec in procurement_officer_ids:
                if not self.is_offer_submitted:
                    self.activity_schedule('ag_field_service.mail_activity_submit_offer', user_id=rec.id)
                if self.state == 'purchase':
                    domain = [
                            ('res_model', '=', 'purchase.order'),
                            ('res_id', 'in', self.ids),
                            ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_send_po_to_vendor').id]),
                        ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        activities.sudo().action_feedback(feedback="PO Sent by Procurement Officer")
                    facility_manager_id = self.branch_id.facility_manager_id
                    technician_id = self.project_task_id.technician_engineer
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = base_url + '/web#id=%s&view_type=form&model=project.task' %(self.project_task_id.id)
                    template_id = self.env.ref('ag_field_service.ag_po_completed_email_template')
                    ctx = dict(self.env.context or {})
                    store_officer_id = self.location.store_officer_id
                    # group_id = self.env.ref('purchase.group_purchase_manager')
                    # for user in group_id.users:
                    #     self.activity_schedule('ag_field_service.mail_activity_po_supply', user_id=user.id)
                    if store_officer_id:
                        self.activity_schedule('ag_field_service.mail_activity_po_supply', user_id=store_officer_id.id)
                    for user in [facility_manager_id, technician_id]:
                        if self.project_task_id:
                            self.project_task_id.activity_schedule('ag_field_service.mail_activity_coordinate_with_vendor', user_id=user.id)
                            ctx.update({
                                'email_to': user.email,
                                'name': user.name,
                                'url': url,
                                'submit_by': "COO",
                            })
                            mail_id = template_id.with_context(ctx).send_mail(self.project_task_id.id, force_send=True)
        return res

    def action_po_submit_offer(self):
        domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_submit_offer').id]),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Offer Submitted by Procurement Officer")
        self.is_offer_submitted = True
        procurement_manager_id = self.env.company.procurement_manager_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=%s&view_type=form&model=purchase.order' % self.id
        template_id = self.env.ref('ag_field_service.ag_po_confirm_email_template')
        ctx = dict(self.env.context or {})
        if procurement_manager_id:
            for rec in procurement_manager_id:
                self.activity_schedule('ag_field_service.mail_activity_confirm_po', user_id=rec.id)
                ctx.update({
                        'email_to': rec.email,
                        'name': rec.name,
                        'url': url,
                        'submit_by': "Procurement Officer",
                    })
                mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)

    def action_return_offer_for_review(self):
        self.is_offer_submitted = False
        domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_confirm_po').id]),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Offer Returned for Review")
        procurement_officer_ids = self.env.company.procurement_user_ids
        for rec in procurement_officer_ids:
            self.activity_schedule('ag_field_service.mail_activity_submit_offer', user_id=rec.id)

    def _approval_allowed(self):
        """Returns whether the order qualifies to be approved by the current user"""
        self.ensure_one()
        # purchase_manager_id = self.env.company.procurement_manager_id
        general_manager_id = self.env.company.general_manager_id
        current_user = self.env.user
        return (
            self.company_id.po_double_validation == 'one_step'
            or (self.company_id.po_double_validation == 'two_step'
                and self.amount_total < self.env.company.currency_id._convert(
                    self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
                    self.date_order or fields.Date.today()))
            or current_user.id == general_manager_id.id) 

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
                general_manager_id = self.env.company.general_manager_id
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=%s&view_type=form&model=purchase.order' % self.id
                template_id = self.env.ref('ag_field_service.ag_po_approve_email_template')
                ctx = dict(self.env.context or {})
                self.activity_schedule('ag_field_service.mail_activity_approve_po', user_id=general_manager_id.id)
                ctx.update({
                    'email_to': general_manager_id.email,
                    'name': general_manager_id.name,
                    'url': url,
                    'submit_by': "Procurement Manager",
                })
                mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
            domain = [
                    ('res_model', '=', 'purchase.order'),
                    ('res_id', 'in', self.ids),
                    ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_confirm_po').id]),
                ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="PO Confirmed by Procurement Manager.")
        return True


    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve(force)
        domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_approve_po').id]),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="PO Approved by COO.")
        # if self.state not in ['purchase', 'done']:
        #     self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
        #     self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        procurement_officer_ids = self.env.company.procurement_user_ids
        if procurement_officer_ids:
            for rec in procurement_officer_ids:
                self.activity_schedule('ag_field_service.mail_activity_send_po_to_vendor', user_id=rec.id)
        
        return res

    def button_receive_orders(self):
        domain = [
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_po_supply').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Purchase Order Supply Validated")
        # group_id = self.env.ref('purchase.group_purchase_user')
        for user in self.env.company.account_payable_user_ids:
            domain = [
                ('res_model', '=', 'purchase.order'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_create_vendor_bill').id),
                ('user_id', '=', user.id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.activity_schedule('ag_field_service.mail_activity_create_vendor_bill', user_id=user.id)
        self.is_order_received = True

    def action_admin_approve(self):
        self.button_approve(force=True)
        if self.state != 'purchase':
            self.write({'state': 'purchase', 'date_approve': fields.Datetime.now()})
            self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}


    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if not self.requisition_id:
            return
        self = self.with_company(self.company_id)
        requisition = self.requisition_id
        if self.partner_id:
            partner = self.partner_id
        else:
            partner = requisition.vendor_id
        project_task_id = requisition.project_task_id
        payment_term = partner.property_supplier_payment_term_id

        FiscalPosition = self.env['account.fiscal.position']
        fpos = FiscalPosition.with_company(self.company_id).get_fiscal_position(partner.id)
        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id,
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        self.branch_id = requisition.branch_id.id
        # if not self.origin or requisition.name not in self.origin.split(', '):
        #     if self.origin:
        #         if requisition.name:
        #             self.origin = self.origin + ', ' + requisition.name
        #     else:
        #         self.origin = requisition.name
        if not self.origin or requisition.origin not in self.origin.split(', '):
            if self.origin:
                if requisition.origin:
                    self.origin = self.origin + ', ' + requisition.origin
            else:
                self.origin = requisition.origin
        self.notes = requisition.description
        self.date_order = fields.Datetime.now()
        self.project_task_id = project_task_id.id

        if requisition.type_id.line_copy != 'copy':
            return

        # Create PO lines if necessary
        order_lines = []
        for line in requisition.line_ids:
            # Compute name
            product_lang = line.product_id.with_context(
                lang=partner.lang or self.env.user.lang,
                partner_id=partner.id
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase

            # Compute taxes
            taxes_ids = fpos.map_tax(line.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == requisition.company_id)).ids

            # Compute quantity and price_unit
            if line.product_uom_id != line.product_id.uom_po_id:
                product_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_po_id)
                price_unit = line.product_uom_id._compute_price(line.price_unit, line.product_id.uom_po_id)
            else:
                product_qty = line.product_qty
                price_unit = line.price_unit

            if requisition.type_id.quantity_copy != 'copy':
                product_qty = 0

            # Create PO line
            order_line_values = line._prepare_purchase_order_line(
                name=name, product_qty=product_qty, price_unit=price_unit,
                taxes_ids=taxes_ids)
            order_lines.append((0, 0, order_line_values))
        self.order_line = order_lines


    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        domain = [
            ('res_model', '=', 'purchase.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_create_vendor_bill').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Vendor Bill Created")

        user_ids = self.env.company.hoa_authorizer
        for user in user_ids:
            for rec in self.invoice_ids:
                domain = [
                    ('res_model', '=', 'account.move'),
                    ('res_id', 'in', rec.ids),
                    ('user_id', 'in', user.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_validate_vendor_bill').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    rec.activity_schedule('ag_field_service.mail_activity_validate_vendor_bill', user_id=user.id)
        return res


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    project_task_id = fields.Many2one("project.task", string="Job Order", copy=False)
    # invisible_approve = fields.Boolean("Invisible Approve", copy=False, compute="_compute_invisible_approve")
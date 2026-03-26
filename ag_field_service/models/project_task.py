# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError, UserError


class Task(models.Model):
    _inherit = "project.task"
    # _rec_name = "jo_number"

    def name_get(self):
        result = []
        for record in self:
            if record.jo_number:
                result.append((record.id, record.jo_number))
            else:
                result.append((record.id, record.name))
        return result
    
    partner_name = fields.Char("Resident Name", copy=False)
    partner_email = fields.Char("Email", copy=False)
    flat_type = fields.Many2one("flat.type", string="Flat Type", copy=False)
    site_id = fields.Many2one('res.branch', string='Site', copy=False)
    appartment_status = fields.Selection([('Vacant', 'Vacant'), ('Occupied', 'Occupied'), ('Consficated', 'Consficated')], string="Apartment Status", copy=False)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    technician_engineer = fields.Many2one('res.users', string="Technician", tracking=True)
    fs_type = fields.Many2one("helpdesk.ticket.type", string='Type', copy=False)
    fs_type_scope = fields.Selection(related="fs_type.scope", store=True)
    user_id = fields.Many2one('res.users', string="Facility Manager", copy=False, default=lambda self: self.env.user.branch_id.facility_manager_id.id)
    equipment_ids = fields.One2many('equipment.items','task_id', string="Equipment Lines", copy=False)
    total_amount = fields.Monetary("Total Amount", compute="_compute_total_amount", store=True)
    findings = fields.Text("Findings", copy=False)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments", copy=False)
    create_jo = fields.Boolean("Create Job Order", copy=False)
    job_order_status = fields.Selection([('fm_not_approved','FM Not Approved'),
                                        ('gm_not_approved','GM Not Approved'),
                                        ('product_not_release','Product Not Released'),
                                        ('rfq_not_created','RFQ Not Created'),
                                        ('pa_not_created','Purchase Agreement Not Created'),
                                        ('jo_not_complete','JO Not Complete'),
                                        ('jo_not_close','JO Not Close')], string="JO Status", compute="_compute_job_order_status")
    jo_type = fields.Selection([('internal_fulfilment', 'Internal Fulfilment'), ('third_party_fulfilment', 'Third Party Fulfilment')], string="Job Order Type", copy=False)
    supporting_document = fields.Binary("Supporting Document", copy=False)
    consent_form = fields.Binary("Resident Consent Form", copy=False)
    job_completion_summary = fields.Text("Job Completion Summary", copy=False)
    job_satisfaction_feedback = fields.Binary("Job Satisfaction Feedback", copy=False)
    technician_submit_jo = fields.Boolean("Technician Submit JO", copy=False)
    fm_approved_jo = fields.Boolean("Facility Manager Approved JO", copy=False)
    gm_approved_jo = fields.Boolean("General Manager Approved JO", copy=False)
    product_released = fields.Boolean("Products Released for JO", copy=False)
    rfq_created = fields.Boolean("RFQ Created", copy=False)
    purchase_agreement_created = fields.Boolean("Purchase Agreement Created", copy=False)
    jo_complete = fields.Boolean("JO Completed", copy=False)
    jo_close = fields.Boolean("JO Close", copy=False)
    equipment_id = fields.Many2one("common.equipment", string="Equipment", copy=False)
    jo_number = fields.Char("Job Order Number", copy=False)
    is_fm_editable = fields.Boolean("Is Facility Manager Editable?", copy=False, compute="_compute_job_order_status")
    procurement_type = fields.Selection([('prefered_vendor', 'Prefered Vendor'), ('call_for_tendor', 'Call for Tender')], string="Procurement Type", copy=False)
    vendor_id = fields.Many2one('res.partner', string="Vendor", copy=False)

    @api.depends('equipment_ids', 'equipment_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.equipment_ids.mapped('amount'))

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.contact_type == 'Resident':
            self.flat_type = self.partner_id.flat_type.id
            self.site_id = self.partner_id.branch_id.id
            self.appartment_status = self.partner_id.appartment_status
            if self.partner_id.residence_type == 'Landlord':
                self.partner_name = self.partner_id.landlord_name
                self.partner_email = self.partner_id.landlord_email
                self.partner_phone = self.partner_id.landlord_contact
            elif self.partner_id.residence_type == 'Tenant':
                self.partner_name = self.partner_id.tenant_name
                self.partner_email = self.partner_id.tenant_email
                self.partner_phone = self.partner_id.tenant_contact

    def write(self, vals):
        res = super(Task, self).write(vals)
        for rec in self:
            if 'create_jo' in vals and not rec.findings:
                raise ValidationError("You cannot create Job Order without Findings!")
            if 'technician_engineer' in vals:
                domain = [
                        ('res_model', '=', 'project.task'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_assign_technician').id),
                    ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    activities.sudo().action_feedback(feedback="Technician Assigned")
                rec.activity_schedule('ag_field_service.mail_activity_field_service_assign', user_id=vals.get('technician_engineer'))
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=%s&view_type=form&model=project.task' % rec.id
                template_id = self.env.ref('ag_field_service.ag_field_service_assign_email_template')
                ctx = dict(self.env.context or {})
                ctx.update({
                        'email_to': rec.technician_engineer.email,
                        'name': rec.technician_engineer.name,
                        'url': url,
                    })
                mail_id = template_id.with_context(ctx).send_mail(rec.id, force_send=True)
        return res

    def action_submit_job_order(self):
        if self.jo_type == 'internal_fulfilment' and not self.equipment_ids:
            raise ValidationError("Cannot Submit Blank JO!")
        if self.fs_type_scope != 'common_area_maintenance' and not self.consent_form:
            raise ValidationError("Please Upload the Consent Form!")
        facility_manager_id = self.site_id.facility_manager_id
        self.technician_submit_jo = True
        domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_field_service_assign').id),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Visit to field for Review")
        self.activity_schedule('ag_field_service.mail_activity_fm_approve_jo', user_id=facility_manager_id.id)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
        template_id = self.env.ref('ag_field_service.ag_jo_approval_email_template')
        ctx = dict(self.env.context or {})
        ctx.update({
                'email_to': facility_manager_id.email,
                'name': facility_manager_id.name,
                'url': url,
                'submit_by': "Technician",
            })
        mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)

    def action_reject_jo(self):
        if self.technician_submit_jo and not self.fm_approved_jo:
            self.technician_submit_jo = False
            domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_fm_approve_jo').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Facility Manager Rejected JO.")
            else:
                domain = [
                    ('res_model', '=', 'project.task'),
                    ('res_id', 'in', self.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_field_service_assign').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    activities.sudo().action_feedback(feedback="Facility Manager Rejected JO.")
            self.activity_schedule('ag_field_service.mail_activity_field_service_assign', user_id=self.technician_engineer.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
            template_id = self.env.ref('ag_field_service.ag_field_service_assign_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': self.technician_engineer.email,
                    'name': self.technician_engineer.name,
                    'url': url,
                })
            mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)
        elif self.technician_submit_jo and self.fm_approved_jo and not self.gm_approved_jo:
            self.fm_approved_jo = False
            domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_gm_approve_jo').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                if self.fs_type_scope != 'common_area_maintenance':
                    activities.sudo().action_feedback(feedback="COO Rejected JO.")
                else:
                    activities.sudo().action_feedback(feedback="Engineering Manager Rejected JO.")
            self.activity_schedule('ag_field_service.mail_activity_field_service_assign', user_id=self.user_id.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
            template_id = self.env.ref('ag_field_service.ag_field_service_assign_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': self.user_id.email,
                    'name': self.user_id.name,
                    'url': url,
                })
            mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)

    def action_fm_approve_jo(self):
        self.fm_approved_jo = True
        domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', 'in', [self.env.ref('ag_field_service.mail_activity_fm_approve_jo').id, self.env.ref('ag_field_service.mail_activity_field_service_assign').id]),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Facility Manager Approved JO.")
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
        ctx = dict(self.env.context or {})
        if self.jo_type == 'internal_fulfilment':
            template_id = self.env.ref('ag_field_service.ag_jo_approval_email_template')
            if self.fs_type_scope != 'common_area_maintenance':
                general_manager_id = self.env.company.general_manager_id
                self.activity_schedule('ag_field_service.mail_activity_gm_approve_jo', user_id=general_manager_id.id)
                ctx.update({
                        'email_to': general_manager_id.email,
                        'name': general_manager_id.name,
                        'url': url,
                        'submit_by': "Facility Manager",
                    })
            else:
                engineering_manager_id = self.env.company.engineering_manager_id
                self.activity_schedule('ag_field_service.mail_activity_gm_approve_jo', user_id=engineering_manager_id.id)
                ctx.update({
                        'email_to': engineering_manager_id.email,
                        'name': engineering_manager_id.name,
                        'url': url,
                        'submit_by': "Facility Manager",
                    })
        else:
            template_id = self.env.ref('ag_field_service.ag_procurement_officer_action_email_template')
            # if self.fs_type_scope != 'common_area_maintenance':
            procurement_user_ids = self.company_id.procurement_user_ids
            for procurement_user_id in procurement_user_ids:
                self.activity_schedule('ag_field_service.mail_activity_procurement_officer_action', user_id=procurement_user_id.id)
                ctx.update({
                        'email_to': procurement_user_id.email,
                        'name': procurement_user_id.name,
                        'url': url,
                        'submit_by': "Facility Manager",
                    })
            # else:
            #     engineering_manager_id = self.env.company.engineering_manager_id
            #     self.activity_schedule('ag_field_service.mail_activity_procurement_officer_action', user_id=engineering_manager_id.id)
            #     ctx.update({
            #             'email_to': engineering_manager_id.email,
            #             'name': engineering_manager_id.name,
            #             'url': url,
            #             'submit_by': "Facility Manager",
            #         })
        mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)

    def action_create_rfq(self):
        if not self.procurement_type:
            raise ValidationError("Please Select the Procurement Type!")
        if self.jo_type == 'third_party_fulfilment' and not self.equipment_ids:
            raise ValidationError("Cannot Create Blank RFQ!")
        if not self.jo_number:
            seq = self.env['ir.sequence'].next_by_code('project.task.order.jo')
            self.jo_number = seq
        if self.env.company.sudo().po_double_validation != 'two_step':
            self.env.company.sudo().po_double_validation = 'two_step'
        order_line = []
        for line in self.equipment_ids:
            vals = {
                'product_id': line.product_id.id,
                'product_qty': line.qty,
                'product_uom': line.product_id.uom_id.id,
                'price_unit': line.price_unit,
                'name': line.product_id.name,
            }
            order_line.append((0, 0, vals))
        purchase_id = self.env['purchase.order'].create({
                'partner_id': self.vendor_id.id,
                'origin': self.jo_number,
                'order_line': order_line,
                'project_task_id': self.id,
                'branch_id': self.site_id.id
            })
        self.rfq_created = True
        domain = [
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_procurement_officer_action').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="RFQ Created")
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request for Quotation'),
            'res_model': 'purchase.order',
            'res_id': purchase_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('purchase.purchase_order_form').id,
            'context': {
                'quotation_only': True
            }
        }

    def action_create_purchase_agreement(self):
        if not self.procurement_type:
            raise ValidationError("Please Select the Procurement Type!")
        if self.jo_type == 'third_party_fulfilment' and not self.equipment_ids:
            raise ValidationError("Cannot Create Blank RFQ!")
        if not self.jo_number:
            seq = self.env['ir.sequence'].next_by_code('project.task.order.jo')
            self.jo_number = seq
        order_line = []
        for line in self.equipment_ids:
            vals = {
                'product_id': line.product_id.id,
                'product_qty': line.qty,
                'product_uom_id': line.product_id.uom_id.id,
                'price_unit': line.price_unit,
                'product_description_variants': line.product_id.name,
            }
            order_line.append((0, 0, vals))
        purchase_agreement_id = self.env['purchase.requisition'].create({
                'vendor_id': self.vendor_id.id,
                'origin': self.jo_number,
                'line_ids': order_line,
                'project_task_id': self.id,
                'branch_id': self.site_id.id,
            })
        self.purchase_agreement_created = True
        domain = [
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_procurement_officer_action').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Purchase Agreement Created")
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Agreement'),
            'res_model': 'purchase.requisition',
            'res_id': purchase_agreement_id.id,
            'view_mode': 'form',
            'view_id': self.env.ref('purchase_requisition.view_purchase_requisition_form').id,
            'context': {}
        }
    
    def action_gm_approve_jo(self):
        if not self.jo_number:
            seq = self.env['ir.sequence'].next_by_code('project.task.order.jo')
            self.jo_number = seq
        store_officer_ids = self.site_id.store_user_ids
        self.gm_approved_jo = True
        domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_gm_approve_jo').id),
            ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            if self.fs_type_scope != 'common_area_maintenance':
                activities.sudo().action_feedback(feedback="COO Approved JO.")
            else:
                activities.sudo().action_feedback(feedback="Engineering Manager Approved JO.")
        if self.equipment_ids:
            for user in store_officer_ids: 
                self.activity_schedule('ag_field_service.mail_activity_release_products', user_id=user.id)
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
                template_id = self.env.ref('ag_field_service.ag_release_products_email_template')
                ctx = dict(self.env.context or {})
                ctx.update({
                        'email_to': user.email,
                        'name': user.name,
                        'url': url,
                        'jo_number': self.jo_number,
                    })
                mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)
        user_ids = self.site_id.facility_manager_id.ids
        user_ids.extend(self.company_id.procurement_user_ids.ids)
        user_ids.extend(self.company_id.account_receviable_user_ids.ids)
        user_ids.extend(self.technician_engineer.ids)
        user_ids = list(dict.fromkeys(user_ids))
        for user in user_ids:
            user_id = self.env['res.users'].sudo().browse(user)
            self.message_subscribe(partner_ids=user_id.partner_id.ids)

    def action_release_products(self):
        self.product_released = True
        warehouse_id = self.env['stock.warehouse'].sudo().search([('branch_id', '=', self.site_id.id)], limit=1)
        location_id = self.env['stock.location'].sudo().search([('usage', '=', 'customer')], limit=1)
        if warehouse_id:
            move_line = []
            for line in self.equipment_ids:
                vals = {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
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
                    'origin': self.jo_number,
                    'move_ids_without_package': move_line,
                    'project_task_id': self.id,
                })
            picking_id.action_confirm()
            picking_id.move_lines._set_quantities_to_reservation()
            picking_id.with_context(skip_immediate=True).button_validate()
            domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_release_products').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="Product Released")
            technician_id = self.technician_engineer
            self.activity_schedule('ag_field_service.mail_activity_complete_jo', user_id=technician_id.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
            template_id = self.env.ref('ag_field_service.ag_products_released_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': technician_id.email,
                    'name': technician_id.name,
                    'url': url,
                    'jo_number': self.jo_number,
                })
            mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)


    def action_jo_completed(self):
        self.jo_complete = True
        if self.jo_type == 'third_party_fulfilment':
            domain = [
                ('res_model', '=', 'project.task'),
                ('res_id', 'in', self.ids),
                ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_coordinate_with_vendor').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="JO Done by Vendor")
        if not self.job_completion_summary:
            raise ValidationError("Please provide the Job Completion Summary!")
        if not self.job_satisfaction_feedback:
            raise ValidationError("Please Upload the JO Satisfaction Feedback!")
        if self.fs_type_scope != 'common_area_maintenance':
            self.activity_schedule('ag_field_service.mail_activity_close_jo', user_id=self.user_id.id)
        else:
            self.activity_schedule('ag_field_service.mail_activity_close_equipment_jo', user_id=self.user_id.id)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=%s&view_type=form&model=project.task' % self.id
        template_id = self.env.ref('ag_field_service.ag_jo_close_email_template')
        ctx = dict(self.env.context or {})
        ctx.update({
                'email_to': self.user_id.email,
                'name': self.user_id.name,
                'url': url,
                'submit_by': "Technician",
            })
        mail_id = template_id.with_context(ctx).send_mail(self.id, force_send=True)

    def action_jo_close(self):
        self.jo_close = True
        if self.fs_type_scope != 'common_area_maintenance':
            expense_history_id = self.env['expense.history'].create({
                    'partner_id': self.partner_id.id,
                    'date': fields.date.today(),
                    'expense_amount': self.total_amount,
                    'ref': "Payment for JO:- %s" %(self.jo_number),
                })
            domain = [
                    ('res_model', '=', 'project.task'),
                    ('res_id', 'in', self.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_close_jo').id),
                ]
        else:
            expense_history_id = self.env['expense.history'].create({
                    'common_equipment_id': self.equipment_id.id,
                    'date': fields.date.today(),
                    'expense_amount': self.total_amount,
                    'ref': "Payment for JO:- %s" %(self.jo_number),
                })
            domain = [
                    ('res_model', '=', 'project.task'),
                    ('res_id', 'in', self.ids),
                    ('activity_type_id', '=', self.env.ref('ag_field_service.mail_activity_close_equipment_jo').id),
                ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="JO Closed")
        if self.fs_type_scope != 'common_area_maintenance':
            self.helpdesk_ticket_id.activity_schedule('ag_field_service.mail_activity_close_ticket', user_id=self.helpdesk_ticket_id.create_uid.id)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=%s&view_type=form&model=helpdesk.ticket' % self.helpdesk_ticket_id.id
            template_id = self.env.ref('ag_field_service.ag_close_ticket_email_template')
            ctx = dict(self.env.context or {})
            ctx.update({
                    'email_to': self.helpdesk_ticket_id.create_uid.email,
                    'name': self.helpdesk_ticket_id.create_uid.name,
                    'url': url,
                })
            mail_id = template_id.with_context(ctx).send_mail(self.helpdesk_ticket_id.id, force_send=True)


    @api.depends('technician_submit_jo', 'fm_approved_jo', 'gm_approved_jo', 'user_id')
    def _compute_job_order_status(self):
        technician_id = self.technician_engineer
        facility_manager_id = self.user_id
        general_manager_id = self.env.company.general_manager_id
        store_officer_ids = self.site_id.store_user_ids
        engineering_manager_id = self.env.company.engineering_manager_id
        procurement_user_ids = self.env.company.procurement_user_ids.ids
        procurement_user_ids.append(engineering_manager_id.id)
        current_user = self.env.user
        for rec in self:
            if current_user.has_group('base.user_admin'):
                rec.is_fm_editable = True
            elif current_user.id == general_manager_id.id:
                rec.is_fm_editable = True
            else:
                rec.is_fm_editable = False
            rec.job_order_status = False
            if rec.technician_submit_jo:
                if not rec.fm_approved_jo and current_user.id == facility_manager_id.id:
                    rec.job_order_status = 'fm_not_approved'

                if rec.jo_type == 'internal_fulfilment' and rec.fm_approved_jo and not rec.gm_approved_jo and current_user.id in [general_manager_id.id, engineering_manager_id.id]:
                    rec.job_order_status = 'gm_not_approved'
                if rec.jo_type == 'internal_fulfilment' and rec.fm_approved_jo and rec.gm_approved_jo and not rec.product_released and current_user.id in store_officer_ids.ids:
                    rec.job_order_status = 'product_not_release'
                if rec.jo_type == 'internal_fulfilment' and rec.fm_approved_jo and rec.gm_approved_jo and rec.product_released and not rec.jo_complete and current_user.id == technician_id.id:
                    rec.job_order_status = 'jo_not_complete'
                if rec.jo_type == 'internal_fulfilment' and rec.fm_approved_jo and rec.gm_approved_jo and rec.product_released and rec.jo_complete and not rec.jo_close and current_user.id == facility_manager_id.id:
                    rec.job_order_status = 'jo_not_close'

                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'prefered_vendor' and rec.fm_approved_jo and not rec.rfq_created and current_user.id in procurement_user_ids:
                    rec.job_order_status = 'rfq_not_created'
                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'prefered_vendor' and rec.fm_approved_jo and rec.rfq_created and not rec.jo_complete and current_user.id == technician_id.id:
                    rec.job_order_status = 'jo_not_complete'
                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'prefered_vendor' and rec.fm_approved_jo and rec.rfq_created and rec.jo_complete and not rec.jo_close and current_user.id == facility_manager_id.id:
                    rec.job_order_status = 'jo_not_close'

                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'call_for_tendor' and rec.fm_approved_jo and not rec.purchase_agreement_created and current_user.id in procurement_user_ids:
                    rec.job_order_status = 'pa_not_created'
                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'call_for_tendor' and rec.fm_approved_jo and rec.purchase_agreement_created and not rec.jo_complete and current_user.id == technician_id.id:
                    rec.job_order_status = 'jo_not_complete'
                if rec.jo_type == 'third_party_fulfilment' and rec.procurement_type == 'call_for_tendor' and rec.fm_approved_jo and rec.purchase_agreement_created and rec.jo_complete and not rec.jo_close and current_user.id == facility_manager_id.id:
                    rec.job_order_status = 'jo_not_close'

    
class EquipmentItems(models.Model):
    _name = 'equipment.items'
    _description = 'Products for JO'
    
    task_id = fields.Many2one('project.task')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    product_id = fields.Many2one('product.product', string='Item')
    qty = fields.Integer('Quantity', default=1)
    price_unit = fields.Float("Unit Price")
    amount = fields.Monetary("Amount", compute="_compute_amount", store=True)
    notes = fields.Text('Notes')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.price_unit = rec.product_id.list_price
    
    @api.depends('qty', 'price_unit')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.qty * rec.price_unit
    
    




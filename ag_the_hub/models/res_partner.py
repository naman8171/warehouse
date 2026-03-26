# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
import datetime
import datetime as DT


class ResUsers(models.Model):
    _inherit = "res.users"

    welcome_done = fields.Boolean()



class SaleOrder(models.Model):
    _inherit = "sale.order"


    wro_id = fields.Many2one("warehouse.receive.order")
    wo_id = fields.Many2one("thehub.workorder")


class ResPartner(models.Model):
    _inherit = "res.partner"


    is_sub_account = fields.Boolean(string="Is Sub-Account", default=False)

    def get_recipient_address(self, partner_id):
        partner_id = self.sudo().search([('id', '=', partner_id)])
        complete_add=''
        if partner_id:
            if partner_id.street:
                complete_add=complete_add+partner_id.street+"\r\n"
            if partner_id.street2:
                complete_add=complete_add+partner_id.street2+"\r\n"
            if partner_id.city:
                complete_add=complete_add+partner_id.city+" ,"
            if partner_id.state_id:
                complete_add=complete_add+partner_id.state_id.name+" ,"
            if partner_id.zip:
                complete_add=complete_add+partner_id.zip+"\r\n"
            if partner_id.country_id:
                complete_add=complete_add+partner_id.country_id.name+"\r\n"
            return complete_add

    def action_reassign_sequence(self):
        self.merchant_sequence=self.env['ir.sequence'].next_by_code('res.partner')
    

    business_name = fields.Char("Business Name")
    order_count = fields.Integer("How Many Orders Are You Shipping Per Month?")
    thehub_account_activated = fields.Boolean("The Hub Account Activated", default=False, copy=False)
    show_account_activation_btn = fields.Boolean(string="Show Account Activation Button" ,compute='_compute_show_account_activation_btn')
    merchant_user_id = fields.Many2one("res.users", string="Merchant", domain=[('share', '=', True)])
    merchant_partner_id = fields.Many2one('res.partner', string="Merchant Partner",related="merchant_user_id.partner_id",store=True)
    company_name = fields.Char("Company Name")
    unit = fields.Char("Unit")

    billing_type = fields.Many2one('billing.type', string="Billing Type", copy=False)
    last_billing_date = fields.Date("Last Billing Date")
    merchant_billing_method = fields.Selection([('prepaid', 'Prepaid'),
                                    ('credit', 'Credit')], string="Merchant Billing Type")
    merchant_sequence = fields.Char(default="draft",string="Merchant ID",copy=False,readonly=True)

    restrict_user = fields.Boolean("Restrict User")
    show_account_reactivate_btn=fields.Boolean(string="Show Account Reactivate Button" ,compute='_compute_show_account_reactivation_btn')
    terms_and_condition = fields.Boolean("Terms & Condition")
    storage_type = fields.Selection(related="billing_type.storage_type",string="Storage Type",store=True)
    contact_type = fields.Selection([('Staff','Staff'),('Vendor','Vendor'),('Merchant','Merchant')],string="Type",default="Staff")
    dedicated_location_ids = fields.Many2many('stock.location','location_partner_rel',string="Dedicated Location Id",domain="[('storage_type','=',storage_type)]")
    wo_stock_type = fields.Selection([('fifi','FIFO'),('lifo','LIFO'),('manually','Manual')],string="Out Stock Type",default="fifi")
    update_dedicated_location_ids = fields.Boolean("Update Location", compute="compute_update_dedicated_location_ids", store=True)

    @api.depends('is_sub_account', 'dedicated_location_ids', 'parent_id')
    def compute_update_dedicated_location_ids(self):
        for rec in self:
            if not rec.parent_id:
                rec.dedicated_location_ids = [(6, 0, rec.dedicated_location_ids.ids)]
                for child in rec.child_ids.filtered(lambda x: x.is_sub_account):
                    child.write({
                                    "dedicated_location_ids" :[(6, 0, rec.dedicated_location_ids.ids)]
                                })
            # elif rec.parent_id and rec.is_sub_account:
            #     rec.write({"dedicated_location_ids": [(6, 0, rec.parent_id.dedicated_location_ids.ids)]})
            rec.update_dedicated_location_ids = True


    type = fields.Selection(
        [('contact', 'Sub-Account'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
         ("private", "Private Address"),
        ], string='Address Type',
        default='contact',
        help="Invoice & Delivery addresses are used in sales orders. Private addresses are only visible by authorized users.")
    
    def write(self,vals):
        res = super(ResPartner, self).write(vals)
        if 'dedicated_location_ids' in vals and self.storage_type=='Dedicated':
            order_line=[]
            for location in self.dedicated_location_ids:
                if not location.billing_start:
                    next_billing_date = fields.Date.today() + DT.timedelta(days=self.billing_type.days)
                    location.billing_date = next_billing_date
                    location.billing_start=True
                    if location.storage_type_id:
                        billing_type = self.billing_type
                        storage_type=False
                        for storage_type in billing_type.storage_template_ids:
                            if storage_type.storage_type.id== location.storage_type_id.id:
                                storage_type=storage_type.storage_type
                                break
                        #storage_line_id = storage_line_env.search([('id','in',line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                        #if storage_line_id:
                        order_line.append((0,0,{
                            'product_id':location.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                            'name':'Dedicated Location'+'-'+location.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                            'price_unit':location.storage_type_id.price if not storage_type else storage_type.product_id.price,
                            'product_uom_qty':1
                            }))
                        #print('----------------',storage_type,location.storage_type_id.product_id.name)
            if len(order_line)>0:
                SaleOrder=self.env['sale.order'].sudo()
                sale_order = SaleOrder.create({
                        'partner_id': self.id,
                        'company_id': self.company_id.id if self.company_id else self.env.user.company_id.id,
                        # 'wro_id':self.id,
                        # 'note':'Billing -- '+self.name,
                        'order_line':order_line
                        #'team_id': team.id if team else False,
                    })
                email_act = sale_order.action_quotation_send()
                email_ctx = email_act.get('context', {})
                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                if self.merchant_billing_method=='prepaid':
                    wallet_obj = self.env['website.wallet.transaction']
        
                    sale_order.write({'is_wallet' : True})
                    partner = sale_order.partner_id
                    company_currency = sale_order.company_id.currency_id
                    price = float(sale_order.partner_id.wallet_balance)
                    amount_total = (sale_order.amount_untaxed + sale_order.amount_tax)
                    wallet_balance= price  
                    if wallet_balance >= sale_order.amount_total:
                        sale_order.write({'amount_total': 0.0 })

                    if sale_order.amount_total > wallet_balance:
                        required_balance=sale_order.amount_total-wallet_balance
                        raise ValidationError("Wallet balance is low please topup to the tune of "+str(required_balance)+"to proceed")

                    wallet_create = wallet_obj.sudo().create({ 
                        'wallet_type': 'debit', 
                        'partner_id': sale_order.partner_id.id, 
                        'sale_order_id': sale_order.id, 
                        'reference': 'sale_order', 
                        'amount': amount_total, 
                        'currency_id': company_currency.id, 
                        'status': 'done' 
                    })
                    if wallet_balance >= amount_total:
                        amount = wallet_balance - amount_total
                        sale_order.write({'wallet_used':float(amount_total),'wallet_transaction_id':wallet_create.id })
                        partner.sudo().write({'wallet_balance':amount})
                        sale_order.action_confirm()
                        invoice_id =sale_order.sudo()._create_invoices()
                        invoice_id.action_post()
        return res    



    def generate_invoice_for_merchant(self):
        SaleOrder=self.env['sale.order'].sudo()
        merchand_ids=self.env['res.partner'].sudo().search([('thehub_account_activated','=',True)])
        for merchand_id in merchand_ids:
            wro_ids = self.env['warehouse.receive.order'].sudo().search([('merchand_id','=',merchand_id.id),('status','=','stored')])
            sale_order_line_list=[]
            if not merchand_id.billing_type:
                continue
            sale_order_line=self.env['sale.order.line'].sudo()
            #service_product_id=self.env.ref('ag_the_hub.product_product_service_wr')
            if merchand_id and merchand_id.storage_type=='Shared':
                sale_order=False
                sale_order_generate=False
                for wro_id in wro_ids:
                    if wro_id.last_billing_date and wro_id.last_billing_date == fields.Date.today():
                        if wro_id.shipping_type =='parcel':
                            order_line=[]
                
                            for wro_line in wro_id.wro_single_sku_per_box_ids:
                                for line in wro_line.wro_single_sku_per_box_line_ids:
                                    if line.send_as == "consolidated":
                                        if line.location_id.storage_type_id:
                                            billing_type = wro_id.merchand_id.billing_type
                                            storage_type=False
                                            for storage_type in billing_type.storage_template_ids:
                                                if storage_type.storage_type.id== line.location_id.storage_type_id.id:
                                                    storage_type=storage_type.storage_type
                                                    break

                                            #storage_line_id = storage_line_env.search([('id','in',line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                                            #if storage_line_id:
                                            order_line.append((0,0,{
                                                'product_id':line.location_id.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                                                'name':line.package_number+'-'+line.location_id.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                                                'price_unit':line.location_id.storage_type_id.price if not storage_type else storage_type.product_id.price,
                                                'product_uom_qty':1
                                                }))
                                    else:
                                        for product_line in line.wro_single_sku_per_box_product_line_ids:
                                            if product_line.location_id.storage_type_id:
                                                billing_type = wro_id.merchand_id.billing_type
                                                storage_type=False
                                                for storage_type in billing_type.storage_template_ids:
                                                    if storage_type.storage_type.id== product_line.location_id.storage_type_id.id:
                                                        storage_type=storage_type.storage_type
                                                        break
                                                #storage_line_id = storage_line_env.search([('id','in',product_line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                                                #if storage_line_id:
                                                order_line.append((0,0,{
                                                    'product_id':product_line.location_id.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                                                    'name':product_line.package_number+'-'+product_line.location_id.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                                                    'price_unit':product_line.location_id.storage_type_id.price if not storage_type else storage_type.product_id.price,
                                                    'product_uom_qty':1
                                                    }))
                            next_billing_date = fields.Date.today() + DT.timedelta(days=wro_id.merchand_id.billing_type.days)
                            wro_id.last_billing_date = next_billing_date
                            if len(order_line)>0:
                                SaleOrder=self.env['sale.order'].sudo()
                                sale_order = SaleOrder.create({
                                        'partner_id': wro_id.merchand_id.id,
                                        'company_id': wro_id.merchand_id.company_id.id if wro_id.merchand_id.company_id else self.env.user.company_id.id,
                                        'wro_id':wro_id.id,
                                        'note':'Billing Rule -- '+wro_id.name,
                                        'order_line':order_line
                                        #'team_id': team.id if team else False,
                                    })
                                email_act = sale_order.action_quotation_send()
                                email_ctx = email_act.get('context', {})
                                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                                if wro_id.merchand_id.merchant_billing_method=='prepaid':
                                    wallet_obj = self.env['website.wallet.transaction']
                        
                                    sale_order.write({'is_wallet' : True})
                                    partner = sale_order.partner_id
                                    company_currency = sale_order.company_id.currency_id
                                    price = float(sale_order.partner_id.wallet_balance)
                                    amount_total = (sale_order.amount_untaxed + sale_order.amount_tax)
                                    wallet_balance= price  
                                    if wallet_balance >= sale_order.amount_total:
                                        sale_order.write({'amount_total': 0.0 })

                                    if sale_order.amount_total > wallet_balance:
                                        required_balance=sale_order.amount_total-wallet_balance
                                        raise ValidationError("Wallet balance is low please topup to the tune of "+str(required_balance)+"to proceed")
                                                    
                                        #raise ValidationError("Wallet balance is low please update wallet balance first")
                                        # user_ids = self.env.company.the_hub_account_activation
                                        # for user_id in user_ids:
                                        #     domain = [
                                        #         ('res_model', '=', 'res.partner'),
                                        #         ('res_id', 'in', merchand_id.ids),
                                        #         ('user_id', 'in', user_id.ids),
                                        #         ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_restriction_thehub_account').id),
                                        #     ]
                                        #     activities = self.env['mail.activity'].sudo().search(domain)
                                        #     if not activities:
                                        #         merchand_id.activity_schedule('ag_the_hub.mail_activity_restriction_thehub_account', user_id=user_id.id)
                                        # merchand_id.restrict_user=True
                                        # deduct_amount = sale_order.amount_total - wallet_balance
                                        # sale_order.write({'amount_total': deduct_amount})

                                    wallet_create = wallet_obj.sudo().create({ 
                                        'wallet_type': 'debit', 
                                        'partner_id': sale_order.partner_id.id, 
                                        'sale_order_id': sale_order.id, 
                                        'reference': 'sale_order', 
                                        'amount': amount_total, 
                                        'currency_id': company_currency.id, 
                                        'status': 'done' 
                                    })
                                    if wallet_balance >= amount_total:
                                        amount = wallet_balance - amount_total
                                        sale_order.write({'wallet_used':float(amount_total),'wallet_transaction_id':wallet_create.id })
                                        partner.sudo().write({'wallet_balance':amount})
                                        sale_order.action_confirm()
                                        invoice_id =sale_order.sudo()._create_invoices()
                                        invoice_id.action_post()
                                else:
                                    # limit_validation = sale_order.check_limit()
                                    # if not limit_validation:
                                    #     raise ValidationError("Customer Credit Limit Exceed")
                                    # else:
                                    sale_order.action_confirm()
                                    invoice_id =sale_order.sudo()._create_invoices()
                                    invoice_id.action_post()

                        else:
                            order_line=[]
            
                            for wro_line in wro_id.wro_single_sku_per_pallet_ids:
                                storage_line_env = self.env['storage.type.line'].sudo()
                                for line in wro_line.wro_single_sku_per_pallet_line_ids:
                                    if line.send_as == "consolidated":
                                        if line.location_id.storage_type_id:
                                            billing_type = wro_id.merchand_id.billing_type
                                            storage_type=False
                                            for storage_type in billing_type.storage_template_ids:
                                                if storage_type.storage_type.id== line.location_id.storage_type_id.id:
                                                    storage_type=storage_type.storage_type
                                                    break
                                            #storage_line_id = storage_line_env.search([('id','in',line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                                            #if storage_line_id:
                                            order_line.append((0,0,{
                                                'product_id':line.location_id.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                                                'name':line.package_number+'-'+line.location_id.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                                                'price_unit':line.location_id.storage_type_id.price if not storage_type else storage_type.product_id.price,
                                                'product_uom_qty':1
                                                }))
                                    else:
                                        for product_line in line.wro_single_sku_per_pallet_product_line_ids:
                                            if product_line.location_id.storage_type_id:
                                                billing_type = wro_id.merchand_id.billing_type
                                                storage_type=False
                                                for storage_type in billing_type.storage_template_ids:
                                                    if storage_type.storage_type.id== product_line.location_id.storage_type_id.id:
                                                        storage_type=storage_type.storage_type
                                                        break
                                                #storage_line_id = storage_line_env.search([('id','in',product_line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                                                #if storage_line_id:
                                                order_line.append((0,0,{
                                                    'product_id':product_line.location_id.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                                                    'name':product_line.package_number+'-'+product_line.location_id.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                                                    'price_unit':product_line.location_id.storage_type_id.price if not storage_type else storage_type.product_id.price,
                                                    'product_uom_qty':1
                                                    }))

                            next_billing_date = fields.Date.today() + DT.timedelta(days=wro_id.merchand_id.billing_type.days)
                            wro_id.last_billing_date = next_billing_date
                            if len(order_line)>0:
                                SaleOrder=self.env['sale.order'].sudo()
                                sale_order = SaleOrder.create({
                                        'partner_id': wro_id.merchand_id.id,
                                        'company_id': wro_id.merchand_id.company_id.id if wro_id.merchand_id.company_id else self.env.user.company_id.id,
                                        'wro_id':wro_id.id,
                                        'note':'Billing -- '+wro_id.name,
                                        'order_line':order_line
                                        #'team_id': team.id if team else False,
                                    })
                                email_act = sale_order.action_quotation_send()
                                email_ctx = email_act.get('context', {})
                                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                                if wro_id.merchand_id.merchant_billing_method=='prepaid':
                                    wallet_obj = self.env['website.wallet.transaction']
                        
                                    sale_order.write({'is_wallet' : True})
                                    partner = sale_order.partner_id
                                    company_currency = sale_order.company_id.currency_id
                                    price = float(sale_order.partner_id.wallet_balance)
                                    amount_total = (sale_order.amount_untaxed + sale_order.amount_tax)
                                    wallet_balance= price  
                                    if wallet_balance >= sale_order.amount_total:
                                        sale_order.write({'amount_total': 0.0 })

                                    if sale_order.amount_total > wallet_balance:
                                        required_balance=sale_order.amount_total-wallet_balance
                                        raise ValidationError("Wallet balance is low please topup to the tune of "+str(required_balance)+"to proceed")

                                    wallet_create = wallet_obj.sudo().create({ 
                                        'wallet_type': 'debit', 
                                        'partner_id': sale_order.partner_id.id, 
                                        'sale_order_id': sale_order.id, 
                                        'reference': 'sale_order', 
                                        'amount': amount_total, 
                                        'currency_id': company_currency.id, 
                                        'status': 'done' 
                                    })
                                    if wallet_balance >= amount_total:
                                        amount = wallet_balance - amount_total
                                        sale_order.write({'wallet_used':float(amount_total),'wallet_transaction_id':wallet_create.id })
                                        partner.sudo().write({'wallet_balance':amount})
                                        sale_order.action_confirm()
                                        invoice_id =sale_order.sudo()._create_invoices()
                                        invoice_id.action_post()
                                else:
                                    # limit_validation = sale_order.check_limit()
                                    # if not limit_validation:
                                    #     raise ValidationError("Customer Credit Limit Exceed")
                                    # else:
                                    sale_order.action_confirm()
                                    invoice_id =sale_order.sudo()._create_invoices()
                                    invoice_id.action_post()

            else:
                sale_order=False
                sale_order_generate=False
                order_line=[]
                for location_id in merchand_id.dedicated_location_ids:
                    if location_id.billing_start and location_id.billing_date and location_id.billing_date == fields.Date.today():
                        next_billing_date = fields.Date.today() + DT.timedelta(days=merchand_id.billing_type.days)
                        location_id.billing_date = next_billing_date
                        location_id.billing_start=True
                        if location_id.storage_type_id:
                            billing_type = merchand_id.billing_type
                            storage_type=False
                            for storage_type in billing_type.storage_template_ids:
                                if storage_type.storage_type.id== location_id.storage_type_id.id:
                                    storage_type=storage_type.storage_type
                                    break
                            #storage_line_id = storage_line_env.search([('id','in',line.location_id.storage_type_id.storage_type_line.ids),('billing_type_id','=',billing_type.id)],limit=1)
                            #if storage_line_id:
                            order_line.append((0,0,{
                                'product_id':location_id.storage_type_id.product_id.id if not storage_type else storage_type.product_id.id,
                                'name':'Dedicated Location'+'-'+location_id.storage_type_id.product_id.name if not storage_type else storage_type.product_id.name,
                                'price_unit':location_id.storage_type_id.price if not storage_type else storage_type.product_id.price,
                                'product_uom_qty':1
                                }))
                if len(order_line)>0:
                    SaleOrder=self.env['sale.order'].sudo()
                    sale_order = SaleOrder.create({
                            'partner_id': merchand_id.id,
                            'company_id': merchand_id.company_id.id if merchand_id.company_id else self.env.user.company_id.id,
                            # 'wro_id':self.id,
                            # 'note':'Billing -- '+self.name,
                            'order_line':order_line
                            #'team_id': team.id if team else False,
                        })
                    email_act = sale_order.action_quotation_send()
                    email_ctx = email_act.get('context', {})
                    sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                    if merchand_id.merchant_billing_method=='prepaid':
                        wallet_obj = self.env['website.wallet.transaction']
            
                        sale_order.write({'is_wallet' : True})
                        partner = sale_order.partner_id
                        company_currency = sale_order.company_id.currency_id
                        price = float(sale_order.partner_id.wallet_balance)
                        amount_total = (sale_order.amount_untaxed + sale_order.amount_tax)
                        wallet_balance= price  
                        if wallet_balance >= sale_order.amount_total:
                            sale_order.write({'amount_total': 0.0 })

                        if sale_order.amount_total > wallet_balance:
                            required_balance=sale_order.amount_total-wallet_balance
                            raise ValidationError("Wallet balance is low please topup to the tune of "+str(required_balance)+"to proceed")

                        wallet_create = wallet_obj.sudo().create({ 
                            'wallet_type': 'debit', 
                            'partner_id': sale_order.partner_id.id, 
                            'sale_order_id': sale_order.id, 
                            'reference': 'sale_order', 
                            'amount': amount_total, 
                            'currency_id': company_currency.id, 
                            'status': 'done' 
                        })
                        if wallet_balance >= amount_total:
                            amount = wallet_balance - amount_total
                            sale_order.write({'wallet_used':float(amount_total),'wallet_transaction_id':wallet_create.id })
                            partner.sudo().write({'wallet_balance':amount})
                            sale_order.action_confirm()
                            invoice_id =sale_order.sudo()._create_invoices()
                            invoice_id.action_post()
            
    def _compute_show_account_reactivation_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.the_hub_account_activation
        for rec in self:
            rec.show_account_reactivate_btn = False
            if current_user.id in user_ids.ids and rec.restrict_user:
                domain = [
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_restriction_thehub_account').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_account_reactivate_btn = True


    def _compute_show_account_activation_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.the_hub_account_activation
        for rec in self:
            rec.show_account_activation_btn = False
            if current_user.id in user_ids.ids and not rec.thehub_account_activated:
                domain = [
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_activate_thehub_account').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_account_activation_btn = True



    def action_remove_restriction_thehub_account(self):
        domain = [
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_restriction_thehub_account').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="The Hub Account Restriction Removed")
        self.restrict_user = False

    def action_activate_thehub_account(self):
        if self.merchant_sequence=='draft':
            self.merchant_sequence=self.env['ir.sequence'].next_by_code('res.partner')
        domain = [
            ('res_model', '=', 'res.partner'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_activate_thehub_account').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="The Hub Account Activated")
        self.thehub_account_activated = True

    @api.model_create_multi
    def create(self, vals):
        # if vals.get('merchant_sequence') and vals.get('merchant_sequence')=='draft':
        #     vals['merchant_sequence']=self.env['ir.sequence'].next_by_code('res.partner')
        if isinstance(vals, list):
            if 'parent_id' in vals[0] and vals[0].get('parent_id'):
                parent_id = self.browse(vals[0].get('parent_id'))
                if parent_id:
                    vals[0].update({
                            'contact_type': parent_id.contact_type,
                            'merchant_sequence': parent_id.merchant_sequence,
                            'thehub_account_activated': parent_id.thehub_account_activated,
                            'storage_type': parent_id.storage_type,
                            'billing_type': parent_id.billing_type.id,
                            'dedicated_location_ids': [(6, 0, parent_id.dedicated_location_ids.ids)],
                            'wo_stock_type': parent_id.wo_stock_type,
                            'is_sub_account': True,
                            'business_name': parent_id.business_name,
                            'order_count': parent_id.order_count,
                            'merchant_billing_method': parent_id.merchant_billing_method,
                        })
            if 'child_ids' in vals[0]:
                for a,b,c in vals[0].get('child_ids'):
                    if c['type'] == 'contact':
                        c['contact_type'] =  vals[0].get('contact_type')
        else:
            if 'parent_id' in vals and vals.get('parent_id'):
                parent_id = self.browse(vals.get('parent_id'))
                if parent_id:
                    vals.update({
                            'merchant_sequence': parent_id.merchant_sequence,
                            'thehub_account_activated': parent_id.thehub_account_activated,
                            'storage_type': parent_id.storage_type,
                            'billing_type': parent_id.billing_type.id,
                            'dedicated_location_ids': [(6, 0, parent_id.dedicated_location_ids.ids)],
                            'wo_stock_type': parent_id.wo_stock_type,
                            'is_sub_account': True,
                            'business_name': parent_id.business_name,
                            'order_count': parent_id.order_count,
                            'merchant_billing_method': parent_id.merchant_billing_method,
                        })
            if 'child_ids' in vals:
                for a,b,c in vals.get('child_ids'):
                    if c['type'] == 'contact':
                        c['contact_type'] =  vals.get('contact_type')
        res = super(ResPartner, self).create(vals)
        if res.create_uid._is_public():
            user_ids = self.env.company.the_hub_account_activation
            for user_id in user_ids:
                domain = [
                    ('res_model', '=', 'res.partner'),
                    ('res_id', 'in', res.ids),
                    ('user_id', 'in', user_id.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_activate_thehub_account').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    res.activity_schedule('ag_the_hub.mail_activity_activate_thehub_account', user_id=user_id.id)
        return res


    

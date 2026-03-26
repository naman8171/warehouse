# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import first
import datetime as DT
import calendar

import base64
import xlwt
import xlsxwriter
import io
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from dateutil.relativedelta import relativedelta


class StockMoveLine(models.Model):

    _inherit = "stock.move.line"

    def set_lot_auto(self,lots):
        """
        Create lots using create_multi to avoid too much queries
        As move lines were created by product or by tracked 'serial'
        products, we apply the lot with both different approaches.
        """
        values = []
        lots_by_product = dict()
        for lot in lots:
            if lot.product_id.id not in lots_by_product:
                lots_by_product[lot.product_id.id] = lot
            else:
                lots_by_product[lot.product_id.id] += lot
        for line in self:
            lot = first(lots_by_product[line.product_id.id])
            line.lot_id = lot
            if lot.product_id.tracking == "serial":
                lots_by_product[line.product_id.id] -= lot

class WarehouseReceiveOrder(models.Model):
    _name = "warehouse.receive.order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Warehouse Receive Order"
    _order = 'id desc'

    name = fields.Char("Name", copy=False)
    active = fields.Boolean("Active" , default=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self:self.env.company)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    shipping_type = fields.Selection([('parcel', 'Parcel (standard shipping)'),
                                      ('pallet', 'Palletized container or LTL (less-than-truckload)'),
                                      ('container', 'Floor loaded container')], string="Shipping Type")
    inventory_type_parcel = fields.Selection([('single', 'One SKU per box'),
                                              ('multiple', 'Multiple SKUs per box')], string="Inventory Type")
    inventory_type_pallet = fields.Selection([('single', 'One SKU per pallet'),
                                              ('multiple', 'Multiple SKUs per pallet')], string="Inventory Type")
    pickup_method = fields.Selection([('the_hub', 'The Hub'),
                                              ('order_courier_company', 'Other Courier Company')], string="Pickup Method")
    contact_name = fields.Char("Contact Name")
    picking_address = fields.Char("Contact Address")
    phone = fields.Char("Contact Phone")
    email = fields.Char("Conatct Email")
    courier_company_name = fields.Char("Company")
    tracking_number = fields.Char("Tracking Number")
    arrival_date = fields.Date("Expected Arrival Date")
    received_date = fields.Date("Received Date")

    wro_type = fields.Selection([("New", "New"), ("Returned", "Returned")], string="WRO Type", copy=False, default="New")
    wo_id = fields.Many2one("thehub.workorder", string="Workorder", copy=False)
    wro_line_ids = fields.One2many("wro.lines", "wro_id", string="WRO Lines", copy=False)
    wro_single_sku_per_box_ids = fields.One2many("wro.single.sku.per.box", "wro_id", string="WRO Single SKU Per Box", copy=False)
    wro_single_sku_per_pallet_ids = fields.One2many("wro.single.sku.per.pallet", "wro_id", string="WRO Single SKU Per Pallet", copy=False)

    status = fields.Selection([('request_submitted', 'WRO Request Submitted'),
                                ('picked_up', 'WRO Picked Up'),
                                ('arrived', 'WRO Arrived'),
                                ('received', 'Received'),
                                ('stored','Stored')], string="Status", copy=False)
    location_id = fields.Many2one("stock.location", string="Stock Location", copy=False)
    consolidated_type = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Consolidated Type", copy=False)
    

    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    
    merchand_id = fields.Many2one("res.partner",string="Merchant",required=True)

    dispute_raised = fields.Boolean("Dispute Raised")

    ticket_count = fields.Char("Ticket",compute='_compute_ticket_count')
    picking_count = fields.Char("Ticket",compute='_compute_picking_count')
    dispute_description = fields.Text("Dispute Description")
    show_label_button = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_label_button')
    stored_date = fields.Date("Stored Date",compute="_compute_stored_date",store=True,readonly=False)
    sale_order_count = fields.Integer(compute="_compute_sale_order",string="Sale Order")
    last_billing_date = fields.Date("Last Billing Date")
    third_party_ref = fields.Char("Third Party Ref #")


    def action_line_import(self):
        

        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'name': _('Bulk Import Lines'),
            'res_model': 'bulk.import.lines',
             'target': 'new',
             'context':{'default_wro_id':self.id}
            
            
        }
        return action 









    def get_graph_data(self):
        WRO = self.env['warehouse.receive.order'].sudo()
        domain = [('merchand_id', '=', self.env.user.partner_id.id)]
        data={}
        # for rec in range(11,0,-1):
        #     date = fields.Date.today()-relativedelta(months=rec)
        #     month_new=date.month
        #     year_new=date.year
        #     cm_wro_stored_count = len(WRO.search(domain + [('status', '=', 'stored')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        #     cm_wro_dispute_count = len(WRO.search(domain + [('status', '!=', 'stored'),('dispute_raised','=',True)]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        #     data.update({
        #         month_new:[calendar.month_name[month_new],cm_wro_stored_count,cm_wro_dispute_count]
        #     })
        date = fields.Date.today()
        month_new=date.month
        year_new=date.month
        cm_wro_stored_count = len(WRO.search(domain + [('status', '=', 'stored')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wro_sub_count = len(WRO.search(domain + [('status', '=', 'request_submitted')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wro_rec_count = len(WRO.search(domain + [('status', '=', 'received')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        
        wro_stored_count = len(WRO.search(domain + [('status', '=', 'stored')]))
        wro_sub_count = len(WRO.search(domain + [('status', '=', 'request_submitted')]))
        wro_rec_count = len(WRO.search(domain + [('status', '=', 'received')]))
        list1=[cm_wro_sub_count,cm_wro_rec_count,cm_wro_stored_count]
        list2=[wro_sub_count,wro_rec_count,wro_stored_count]
        
        data.update({'list1':list1,'list2':list2})
        return data

    def delete_wro(self,data):
        wro_ids = self.env['warehouse.receive.order'].sudo().search([('id','in',data)])
        IrConfig = self.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('web.base.url')
        base_url =base_url+'/my/wros'
        for wro_id in wro_ids:
            if wro_id.status in [False]:
                wro_id.sudo().unlink()

        return base_url


    def export_wro_list(self,data):
        IrConfig = self.env['ir.config_parameter'].sudo()

        base_url = IrConfig.get_param('web.base.url')


        


        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('wro_status_report')
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(50 * 260)
        worksheet.col(5).width = int(18 * 260)
        worksheet.col(6).width = int(18 * 260)
        worksheet.col(7).width = int(18 * 260)

        row = 0
        worksheet.write_merge(row, row + 1, 0, 7, 'WRO Report', xlwt.easyxf('font:bold on;alignment: horizontal  center;'))
        row += 2
        row += 3

        worksheet.write(row, 3, 'NAME', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 4, 'WAREHOUSE', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 5, 'SHIPPING TYPE', xlwt.easyxf('font:bold on'))
        
        worksheet.write(row, 6, 'ARRIVAL DATE', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 7, 'STATUS', xlwt.easyxf('font:bold on'))

        row += 1
        # total_qty=0
        # total_price=0
        wro_ids = self.env['warehouse.receive.order'].sudo().search([('id','in',data)])


        for line in wro_ids:
            worksheet.write(row, 3, line.name)
            worksheet.write(row, 4, line.warehouse_id.name)
            worksheet.write(row, 5, str(line.shipping_type if line.shipping_type else ''))
            worksheet.write(row, 6, str(line.arrival_date if line.arrival_date else ''))
            worksheet.write(row, 7, str(line.status if line.status else ''))
            
            
            row += 1

        # worksheet.write(row, 3, 'Total')
        # worksheet.write(row, 4, str("{:.2f}".format(total_qty)))
        # worksheet.write(row, 5, str("{:.2f}".format(total_price)))



        # worksheet.write(row, 0, 'Grand Totals', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 1, str(data.get('total_amount')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 2, '', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 3, str(data.get('total_qty')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 4, str(data.get('total_sales')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 5, '', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 6, str(data.get('total_gross_profit')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 7, '', xlwt.easyxf('font:bold on'))
        # row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        new_file_id = self.env['wizard.update.quantity'].sudo().create({
            'file':base64.encodebytes(fp.getvalue()),
            'filename':'wro_report.xls'
            })
        complete_url = '%s/web/content/?model=wizard.update.quantity&field=file&download=true&id=%s&filename=%s' % (base_url,new_file_id.id, new_file_id.filename)
        return complete_url



    def _compute_sale_order(self):
        for rec in self:
            rec.sale_order_count = self.env['sale.order'].sudo().search_count([('wro_id','=',rec.id)])
            

    def action_view_sale_order(self):
        sale_order_id = self.env['sale.order'].sudo().search([('wro_id','=',self.id)])  
        tree_view_id = self.env.ref('sale.view_quotation_tree').id
        form_view_id = self.env.ref('sale.view_order_form').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'view_mode': 'tree,form',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'domain': [('id','in',sale_order_id.ids)],
            
        }
        return action      

    @api.depends('status')
    def _compute_stored_date(self):
        for rec in self:
            if rec.status=='stored':
                rec.stored_date=fields.Date.today()
    






    def action_open_picking(self):
        picking_ids = self.env['stock.picking'].search([('wro_id','=',self.id)])
        tree_view_id = self.env.ref('stock.vpicktree').id
        form_view_id = self.env.ref('stock.view_picking_form').id
        

        action = {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'view_mode': 'tree,form',
            'name': _('Transfer'),
            'res_model': 'stock.picking',
            'domain': [('id','in',picking_ids.ids)],
            
        }
        return action


    def _compute_label_button(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for rec in self:
            rec.show_label_button = False
            if current_user.id in user_ids.ids:
                
                rec.show_label_button = True

        
        


    def action_raise_dispute_open(self):
        name="Dispute - WRO "+self.name
        ticket_ids = self.env['helpdesk.ticket'].sudo().search([('name','=',name)])
        if len(ticket_ids.ids)==1:
            view = self.env.ref('helpdesk.helpdesk_ticket_view_form')
            return {
                'name': _('Ticket created'),
                'view_mode': 'form',
                'view_id': view.id,
                'res_model': 'helpdesk.ticket',
                'type': 'ir.actions.act_window',
                'res_id': ticket_ids.id,
                'context': self.env.context
            }
            



    def action_raise_dispute(self):
        if not self.dispute_description:
            raise UserError('Please add Dispute reason first')
        team_id=self.env['helpdesk.team'].sudo().search([('name','=','WRO Dispute')],limit=1)

        ticket_data={
        'partner_id':self.merchand_id.id,
        'team_id':team_id.id,
        'name':"Dispute - WRO "+self.name,
        'description':self.dispute_description,
        'wro_id':self.id
        }
        ticket_id = self.env['helpdesk.ticket'].sudo().create(ticket_data)
        self.dispute_raised=True
        for user in team_id.visibility_member_ids:
            ticket_id.sudo().activity_schedule('ag_the_hub.mail_activity_wro_dispute', user_id=user.id)

        body = _("<strong>Your request Dispute - %s has been received and is being reviewed by our WRO Dispute team. The reference of your ticket is %s. And dispute Decription is below :- </div><div style='color:red;'>%s</div>",ticket_id.name,ticket_id.id,self.dispute_description)
            

        self.message_post(body=body)



    def _compute_picking_count(self):
        for rec in self:
            picking_ids = self.env['stock.picking'].search([('wro_id','=',self.id)])
            rec.picking_count=len(picking_ids.ids)


    def _compute_ticket_count(self):
        for rec in self:
            name="Dispute - WRO "+rec.name
            ticket_id = self.env['helpdesk.ticket'].sudo().search([('name','=',name)])
            rec.ticket_count=len(ticket_id.ids)
        

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for rec in self:
            rec.show_picker_btn = False
            if current_user.id in user_ids.ids:
                domain = [
                    ('res_model', '=', 'warehouse.receive.order'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_picker_btn = True



    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for rec in self:
            rec.show_received_done_btn = False
            if current_user.id in user_ids.ids:
                domain = [
                    ('res_model', '=', 'warehouse.receive.order'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_received_done_btn = True

    @api.model
    def create(self, vals):
        res = super(WarehouseReceiveOrder, self).create(vals)
        if not res.name:
            seq = self.env['ir.sequence'].next_by_code('warehouse.receive.order')
            res.name = seq
        return res

    def action_wro_submit(self, wroId):
        if wroId[0]:
            wroId = self.sudo().browse(int(wroId[0]))
            wroId.status = 'request_submitted'
            if wroId.pickup_method == 'the_hub':
                user_ids = self.env.company.sudo().wro_picker_user_ids
                for user_id in user_ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', wroId.ids),
                        ('user_id', '=', user_id.id),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_pick_up_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if not activities:
                        wroId.sudo().activity_schedule('ag_the_hub.mail_activity_pick_up_wro', user_id=user_id.id)
            else:
                user_ids = self.env.company.sudo().receiver_user_ids
                for user_id in user_ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', wroId.ids),
                        ('user_id', '=', user_id.id),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if not activities:
                        wroId.sudo().activity_schedule('ag_the_hub.mail_activity_process_submitted_wro', user_id=user_id.id)
        return True

    def action_wro_picked(self):
        domain = [
            ('res_model', '=', 'warehouse.receive.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_pick_up_wro').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="WRO Pickup Done")
        self.status = "picked_up"

    def action_wro_arrived(self):
        self.status = "arrived"
        user_ids = self.env.company.receiver_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'warehouse.receive.order'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.activity_schedule('ag_the_hub.mail_activity_process_submitted_wro', user_id=user_id.id)
        

        if self.shipping_type =='pallet':
            
            #for line in self.wro_single_sku_per_pallet_ids:
            for rec in self.wro_single_sku_per_pallet_ids:
                consolidated_type=rec.consolidated_type
                wro_single_sku_per_pallet_id = rec
                
                iteration_time=wro_single_sku_per_pallet_id.no_of_pallets
                for i in range(0, int(iteration_time)):
                    # self.env['single.sku.per.pallet.line'].sudo().search([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)]).unlink()
                    pallet_line_id=self.env['single.sku.per.pallet.line'].sudo().create({
                            'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.pallet.line'),
                            'wro_single_sku_per_pallet_id': wro_single_sku_per_pallet_id.id,
                            'send_as':consolidated_type,
                            'location_id':wro_single_sku_per_pallet_id.defaultlocation_id.id if wro_single_sku_per_pallet_id.defaultlocation_id.id and wro_single_sku_per_pallet_id.is_default_location else False
                        })
                    if consolidated_type=='non_consolidated':
                        for j in range(0,int(rec.qty_per_pallet)):
                            pallet_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                'package_number': pallet_line_id.package_number+'/'+str(j+1),
                                'wro_single_sku_per_pallet_line_id': pallet_line_id.id,
                                'location_id':wro_single_sku_per_pallet_id.defaultlocation_id.id if wro_single_sku_per_pallet_id.defaultlocation_id.id and wro_single_sku_per_pallet_id.is_default_location else False
                                
                            })
        else:
            for rec in self.wro_single_sku_per_box_ids:
                consolidated_type=rec.consolidated_type
                wro_single_sku_per_box_id = rec
                
                iteration_time=rec.no_of_boxes

                for i in range(0, int(iteration_time)):
                    # self.env['single.sku.per.box.line'].sudo().search([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)]).unlink()
                    box_line_id = self.env['single.sku.per.box.line'].sudo().create({
                            'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.box.line'),
                            'wro_single_sku_per_box_id': wro_single_sku_per_box_id.id,
                            'send_as':consolidated_type,
                            'location_id':wro_single_sku_per_box_id.defaultlocation_id.id if wro_single_sku_per_box_id.defaultlocation_id.id and wro_single_sku_per_box_id.is_default_location else False
                                
                        })
                    if consolidated_type=='non_consolidated':
                        for j in range(0,int(rec['qty_per_box'])):
                            box_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                'package_number': box_line_id.package_number+'/'+str(j+1),
                                'wro_single_sku_per_box_line_id': box_line_id.id,
                                'location_id':wro_single_sku_per_box_id.defaultlocation_id.id if wro_single_sku_per_box_id.defaultlocation_id.id and wro_single_sku_per_box_id.is_default_location else False
                                
                            })

    def action_wro_received(self):

        if self.shipping_type =='parcel':
            for wro_line in self.wro_single_sku_per_box_ids:
            
                if wro_line.consolidated_type=='consolidated':
                    for box_line in wro_line.wro_single_sku_per_box_line_ids:
                        if not box_line.location_id:
                            raise ValidationError("Please Enter Location First ")
                            break
                else:
                    for box_line in wro_line.wro_single_sku_per_box_line_ids:
                        count=0
                        for line in box_line.wro_single_sku_per_box_product_line_ids:
                            if not line.location_id:
                                count=1
                                raise ValidationError("Please Enter Location First ")
                                break
                        if count>0:
                            break
            SaleOrder=self.env['sale.order'].sudo()
            sale_order_line_obj=self.env['sale.order.line'].sudo()


            sale_order_line=[]
            for line in self.wro_single_sku_per_box_ids:
                if line.consolidated_type=='non_consolidated':
                    sale_order_line.append({
                        'product_id':line.product_id.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_noncons_product.id,
                        'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_noncons_product.name,
                        'product_uom_qty':line.product_qty,
                        'price_unit':self.company_id.incoming_box_cost_noncons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_noncons,
                        })
                else:
                    sale_order_line.append({
                        'product_id':line.product_id.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_cons_product.id,
                        'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_cons_product.name,
                        'product_uom_qty':line.no_of_boxes,
                        'price_unit':self.company_id.incoming_box_cost_cons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_box_cost_cons,
                        })
            if len(sale_order_line)>0:
                sale_order = SaleOrder.create({
                    'partner_id': self.merchand_id.id,
                    'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                    'wro_id':self.id,
                    #'team_id': team.id if team else False,
                })
                for line in sale_order_line:
                    line.update({'order_id':sale_order.id})
                    sale_order_line_id=sale_order_line_obj.create(line)
                    # sale_order_line_id.product_id_change()
                    # sale_order_line_id.write({'name':line['name']})

                email_act = sale_order.action_quotation_send()
                email_ctx = email_act.get('context', {})
                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                if self.merchand_id.merchant_billing_method=='prepaid':
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


            sale_order_line=[]
            for line in self.wro_single_sku_per_box_ids:
                if line.consolidated_type=='consolidated':
                    for box_line in line.wro_single_sku_per_box_line_ids:
                        if box_line.is_package_required and box_line.packing_type_id:
                            packing_template=False
                            if self.merchand_id.billing_type:
                                for rec in self.merchand_id.billing_type.packing_template_ids:
                                    if rec.packing_type_id==box_line.packing_type_id:
                                        packing_template=rec
                                        break
                            sale_order_line.append({
                                'product_id':box_line.packing_type_id.product_id.id if not packing_template else packing_template.product_id.id,
                                'name':self.name+'-'+line.product_id.name,
                                'product_uom_qty':1,
                                'price_unit':box_line.packing_type_id.price if not packing_template else packing_template.price,
                                })
                else:
                    for box_line in line.wro_single_sku_per_box_line_ids:
                        for product_line in box_line.wro_single_sku_per_box_product_line_ids:
                            if product_line.is_package_required and product_line.packing_type_id:
                                packing_template=False
                                if self.merchand_id.billing_type:
                                    for rec in self.merchand_id.billing_type.packing_template_ids:
                                        if rec.packing_type_id==product_line.packing_type_id:
                                            packing_template=rec
                                            break
                                sale_order_line.append({
                                    'product_id':product_line.packing_type_id.product_id.id if not packing_template else packing_template.product_id.id,
                                    'name':self.name+'-'+line.product_id.name,
                                    'product_uom_qty':1,
                                    'price_unit':product_line.packing_type_id.price if not packing_template else packing_template.price,
                                    })
            if len(sale_order_line)>0:
                sale_order = SaleOrder.create({
                    'partner_id': self.merchand_id.id,
                    'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                    'wro_id':self.id,
                    #'team_id': team.id if team else False,
                })
                for line in sale_order_line:
                    line.update({'order_id':sale_order.id})
                    sale_order_line_id=sale_order_line_obj.create(line)
                    # sale_order_line_id.product_id_change()
                    # sale_order_line_id.write({'name':line['name']})

                email_act = sale_order.action_quotation_send()
                email_ctx = email_act.get('context', {})
                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                if self.merchand_id.merchant_billing_method=='prepaid':
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
            for wro_line in self.wro_single_sku_per_pallet_ids:
                if wro_line.consolidated_type =='consolidated':
                
                    for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                        if not pallet_line.location_id:
                            raise ValidationError("Please Enter Location First")
                else:
                    for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                        for line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
                            if not line.location_id:
                                raise ValidationError("Please Enter Location First")


            SaleOrder=self.env['sale.order'].sudo()
            sale_order_line_obj=self.env['sale.order.line'].sudo()


            sale_order_line=[]
            for line in self.wro_single_sku_per_pallet_ids:
                if line.consolidated_type=='non_consolidated':

                    sale_order_line.append({
                        'product_id':line.product_id.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_noncons_product.id,
                        'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_noncons_product.name,
                        'product_uom_qty':line.product_qty,
                        'price_unit':self.company_id.incoming_pallet_cost_noncons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_noncons,
                        })
                else:
                    sale_order_line.append({
                        'product_id':line.product_id.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_cons_product.id,
                        'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_cons_product.name,
                        'product_uom_qty':line.no_of_pallets,
                        'price_unit':self.company_id.incoming_pallet_cost_cons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.incoming_pallet_cost_cons,
                        })
            if len(sale_order_line)>0:
                sale_order = SaleOrder.create({
                    'partner_id': self.merchand_id.id,
                    'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                    'wro_id':self.id,
                    #'team_id': team.id if team else False,
                })
                for line in sale_order_line:
                    line.update({'order_id':sale_order.id})
                    sale_order_line_id=sale_order_line_obj.create(line)
                    # sale_order_line_id.product_id_change()
                    # sale_order_line_id.write({'name':line['name'],'price_unit':line['price_unit']})

                email_act = sale_order.action_quotation_send()
                email_ctx = email_act.get('context', {})
                sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                if self.merchand_id.merchant_billing_method=='prepaid':
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

        # else:
        #     if self.shipping_type =='parcel':
                
        #         for wro_line in self.wro_single_sku_per_box_ids:
        #             line_ids = []
        #             validate=False
        #             for box_line in wro_line.wro_single_sku_per_box_line_ids:
        #                 if validate:
        #                     break
        #                 if not box_line.location_id:
        #                     raise ValidationError("Please Enter Location First")
        #                     break
        #                 for product_line in box_line.wro_single_sku_per_box_product_line_ids:
        #                     if not product_line.location_id:
        #                         raise ValidationError("Please Enter Location First")
        #                         break
        #                         validate=True
        #     else:
        #         for wro_line in self.wro_single_sku_per_pallet_ids:
        #             line_ids = []
        #             validate=False
        #             for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
        #                 if validate:
        #                     break
        #                 if not pallet_line.location_id:
        #                     raise ValidationError("Please Enter Location First")
        #                     break
        #                 for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
        #                     if not product_line.location_id:
        #                         raise ValidationError("Please Enter Location First")
        #                         break
        #                         validate=True
                

                

                    

        
        self.status = "received"
        self.received_date = fields.Date.today()
        user_ids = self.env.company.sudo().wro_picker_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'warehouse.receive.order'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.sudo().activity_schedule('ag_the_hub.mail_activity_picker_process_wro', user_id=user_id.id)
        user_ids = self.env.company.receiver_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'warehouse.receive.order'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if activities:
                activities.sudo().action_feedback(feedback="WRO Received")


    def action_wro_stored(self):
    

        domain = [
            ('res_model', '=', 'warehouse.receive.order'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="WRO Stored")
        self.status = "stored"
        picking_type_id = self.env['stock.picking.type'].sudo().search([('code', '=', 'incoming')], limit=1)
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', self.company_id.id)])
        if not picking_type_id:
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        picking_type_id=picking_type_id[:1]
        #if self.merchand_id.storage_type!='Dedicated':
        if self.shipping_type =='parcel':
            order_line=[]
            if self.merchand_id.storage_type!='Dedicated':   
                for wro_line in self.wro_single_sku_per_box_ids:
                    
                    for box_line in wro_line.wro_single_sku_per_box_line_ids:
                        if box_line.send_as=="consolidated":
                            if not box_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                        else:
                            line_ids = []
                            validate=False
                            for box_line in wro_line.wro_single_sku_per_box_line_ids:
                                if validate:
                                    break
                                if not box_line.is_validated:
                                    raise ValidationError("Please Validate All Box First")
                                    break
                                for product_line in box_line.wro_single_sku_per_box_product_line_ids:
                                    if not product_line.is_validated:
                                        raise ValidationError("Please Validate All Box First")
                                        break
                                        validate=True
                    storage_line_env = self.env['storage.type.line'].sudo()
                    for line in wro_line.wro_single_sku_per_box_line_ids:
                        if line.send_as == "consolidated":
                            if line.location_id.storage_type_id:
                                billing_type = self.merchand_id.billing_type
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
                                    billing_type = self.merchand_id.billing_type
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

                next_billing_date = fields.Date.today() + DT.timedelta(days=self.merchand_id.billing_type.days)
                self.last_billing_date = next_billing_date
                if len(order_line)>0:
                    SaleOrder=self.env['sale.order'].sudo()
                    sale_order = SaleOrder.create({
                            'partner_id': self.merchand_id.id,
                            'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                            'wro_id':self.id,
                            'note':'Billing -- '+self.name,
                            'order_line':order_line
                            #'team_id': team.id if team else False,
                        })
                    email_act = sale_order.action_quotation_send()
                    email_ctx = email_act.get('context', {})
                    sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                    if self.merchand_id.merchant_billing_method=='prepaid':
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

                for wro_line in self.wro_single_sku_per_box_ids:
                

                    for box_line in wro_line.wro_single_sku_per_box_line_ids:
                        if box_line.send_as == "consolidated":
                            lot_id = self.env['stock.production.lot'].sudo().create({
                                'name':box_line.package_number,
                                'product_id':wro_line.product_id.id,
                                'company_id':self.company_id.id,
                                'product_qty':wro_line.qty_per_box
                                })
                            line_ids = []
                            line_ids.append((0,0,{
                                    'product_id': wro_line.product_id.id,
                                    'name': wro_line.product_id.display_name,
                                    'product_uom_qty': wro_line.qty_per_box,
                                    'product_uom': wro_line.product_id.uom_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': box_line.location_id.id,
                                    'lot_ids':[(6,0,lot_id.ids)]
                                }))
                            picking_id = self.env['stock.picking'].sudo().create({
                                    'partner_id':self.merchand_id.id,
                                    'picking_type_id': picking_type_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': box_line.location_id.id,
                                    'move_ids_without_package': line_ids,
                                    'origin': box_line.package_number,
                                    'wro_id':self.id,
                                    'owner_id':self.merchand_id.id
                                })
                            picking_id.action_confirm()
                            for move_line in picking_id.move_line_ids_without_package:
                                move_line.qty_done = move_line.product_uom_qty
                                move_line.lot_id=lot_id.id
                            # picking_id.action_assign()
                            # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
                            lines = picking_id.mapped("move_line_ids").filtered(
                                lambda x: (
                                    not x.lot_id
                                    and not x.lot_name
                                    and x.product_id.tracking != "none"
                                    
                                )
                            )
                            lines.set_lot_auto(lot_id)
                            # for picking_line in picking_id.move_line_ids:
                            #     picking_line.write({'lot_id':lot_id.id})
                            if picking_id.state == 'draft':
                                picking_id.action_confirm()
                            
                            #picking_id.button_validate()
                            picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()

                        else:
                            for product_line in box_line.wro_single_sku_per_box_product_line_ids:
                                lot_id = self.env['stock.production.lot'].sudo().create({
                                        'name':product_line.package_number,
                                        'product_id':wro_line.product_id.id,
                                        'company_id':self.company_id.id,
                                        'product_qty':1
                                        })
                                line_ids = []
                                line_ids.append((0,0,{
                                        'product_id': wro_line.product_id.id,
                                        'name': wro_line.product_id.display_name,
                                        'product_uom_qty': 1,
                                        'product_uom': wro_line.product_id.uom_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'lot_ids':[(6,0,lot_id.ids)]
                                    }))
                                picking_id = self.env['stock.picking'].sudo().create({
                                        'partner_id':self.merchand_id.id,
                                        'picking_type_id': picking_type_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'move_ids_without_package': line_ids,
                                        'origin': product_line.package_number,
                                        'wro_id':self.id,
                                        'owner_id':self.merchand_id.id
                                    })
                                picking_id.action_confirm()
                                for move_line in picking_id.move_line_ids_without_package:
                                    move_line.qty_done = move_line.product_uom_qty
                                    move_line.lot_id=lot_id.id
                                # picking_id.action_assign()
                                # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                                
                                lines = picking_id.mapped("move_line_ids").filtered(
                                    lambda x: (
                                        not x.lot_id
                                        and not x.lot_name
                                        and x.product_id.tracking != "none"
                                        
                                    )
                                )
                                lines.set_lot_auto(lot_id)
                                # for picking_line in picking_id.move_line_ids:
                                #     picking_line.write({'lot_id':lot_id.id})
                                if picking_id.state == 'draft':
                                    picking_id.action_confirm()
                                
                                #picking_id.button_validate()
                                picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()



            else:
                for wro_line in self.wro_single_sku_per_box_ids:
                

                    for box_line in wro_line.wro_single_sku_per_box_line_ids:
                        if box_line.send_as == "consolidated":
                            lot_id = self.env['stock.production.lot'].sudo().create({
                                'name':box_line.package_number,
                                'product_id':wro_line.product_id.id,
                                'company_id':self.company_id.id,
                                'product_qty':wro_line.qty_per_box
                                })
                            line_ids = []
                            line_ids.append((0,0,{
                                    'product_id': wro_line.product_id.id,
                                    'name': wro_line.product_id.display_name,
                                    'product_uom_qty': wro_line.qty_per_box,
                                    'product_uom': wro_line.product_id.uom_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': box_line.location_id.id,
                                    'lot_ids':[(6,0,lot_id.ids)]
                                }))
                            picking_id = self.env['stock.picking'].sudo().create({
                                    'partner_id':self.merchand_id.id,
                                    'picking_type_id': picking_type_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': box_line.location_id.id,
                                    'move_ids_without_package': line_ids,
                                    'origin': box_line.package_number,
                                    'wro_id':self.id,
                                    'owner_id':self.merchand_id.id
                                })
                            picking_id.action_confirm()
                            for move_line in picking_id.move_line_ids_without_package:
                                move_line.qty_done = move_line.product_uom_qty
                                move_line.lot_id=lot_id.id
                            # picking_id.action_assign()
                            # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
                            lines = picking_id.mapped("move_line_ids").filtered(
                                lambda x: (
                                    not x.lot_id
                                    and not x.lot_name
                                    and x.product_id.tracking != "none"
                                    
                                )
                            )
                            lines.set_lot_auto(lot_id)
                            # for picking_line in picking_id.move_line_ids:
                            #     picking_line.write({'lot_id':lot_id.id})
                            if picking_id.state == 'draft':
                                picking_id.action_confirm()
                            
                            #picking_id.button_validate()
                            picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()

                        else:
                            for product_line in box_line.wro_single_sku_per_box_product_line_ids:
                                lot_id = self.env['stock.production.lot'].sudo().create({
                                        'name':product_line.package_number,
                                        'product_id':wro_line.product_id.id,
                                        'company_id':self.company_id.id,
                                        'product_qty':1
                                        })
                                line_ids = []
                                line_ids.append((0,0,{
                                        'product_id': wro_line.product_id.id,
                                        'name': wro_line.product_id.display_name,
                                        'product_uom_qty': 1,
                                        'product_uom': wro_line.product_id.uom_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'lot_ids':[(6,0,lot_id.ids)]
                                    }))
                                picking_id = self.env['stock.picking'].sudo().create({
                                        'partner_id':self.merchand_id.id,
                                        'picking_type_id': picking_type_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'move_ids_without_package': line_ids,
                                        'origin': product_line.package_number,
                                        'wro_id':self.id,
                                        'owner_id':self.merchand_id.id
                                    })
                                picking_id.action_confirm()
                                for move_line in picking_id.move_line_ids_without_package:
                                    move_line.qty_done = move_line.product_uom_qty
                                    move_line.lot_id=lot_id.id
                                # picking_id.action_assign()
                                # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                                
                                lines = picking_id.mapped("move_line_ids").filtered(
                                    lambda x: (
                                        not x.lot_id
                                        and not x.lot_name
                                        and x.product_id.tracking != "none"
                                        
                                    )
                                )
                                lines.set_lot_auto(lot_id)
                                # for picking_line in picking_id.move_line_ids:
                                #     picking_line.write({'lot_id':lot_id.id})
                                if picking_id.state == 'draft':
                                    picking_id.action_confirm()
                                
                                #picking_id.button_validate()
                                picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
        else:
            order_line=[]
            if self.merchand_id.storage_type=='Dedicated':   
            
                for wro_line in self.wro_single_sku_per_pallet_ids:
                    if wro_line.consolidated_type == 'consolidated':
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                    
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            lot_id = self.env['stock.production.lot'].sudo().create({
                                'name':pallet_line.package_number,
                                'product_id':wro_line.product_id.id,
                                'company_id':self.company_id.id,
                                'product_qty':wro_line.qty_per_pallet
                                })
                            line_ids = []
                            line_ids.append((0,0,{
                                    'product_id': wro_line.product_id.id,
                                    'name': wro_line.product_id.display_name,
                                    'product_uom_qty': wro_line.qty_per_pallet,
                                    'product_uom': wro_line.product_id.uom_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': pallet_line.location_id.id,
                                    'lot_ids':[(6,0,lot_id.ids)]
                                }))
                            picking_id = self.env['stock.picking'].sudo().create({
                                    'partner_id':self.merchand_id.id,
                                    'picking_type_id': picking_type_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': pallet_line.location_id.id,
                                    'move_ids_without_package': line_ids,
                                    'origin': pallet_line.package_number,
                                    'wro_id':self.id,
                                    'owner_id':self.merchand_id.id
                                })
                            picking_id.action_confirm()
                            for move_line in picking_id.move_line_ids_without_package:
                                move_line.qty_done = move_line.product_uom_qty
                                move_line.lot_id=lot_id.id
                            # picking_id.action_assign()
                            # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
                            lines = picking_id.mapped("move_line_ids").filtered(
                                lambda x: (
                                    not x.lot_id
                                    and not x.lot_name
                                    and x.product_id.tracking != "none"
                                    
                                )
                            )
                            lines.set_lot_auto(lot_id)
                            # for picking_line in picking_id.move_line_ids:
                            #     picking_line.write({'lot_id':lot_id.id})
                            if picking_id.state == 'draft':
                                picking_id.action_confirm()
                            
                            #picking_id.button_validate()
                            picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
                    else:
                        line_ids = []
                        validate=False
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if validate:
                                break
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                                break
                            for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
                                if not product_line.is_validated:
                                    raise ValidationError("Please Validate All Box First")
                                    break
                                    validate=True
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:

                            for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
                                lot_id = self.env['stock.production.lot'].sudo().create({
                                        'name':product_line.package_number,
                                        'product_id':wro_line.product_id.id,
                                        'company_id':self.company_id.id,
                                        'product_qty':1
                                        })
                                line_ids = []
                                line_ids.append((0,0,{
                                        'product_id': wro_line.product_id.id,
                                        'name': wro_line.product_id.display_name,
                                        'product_uom_qty': 1,
                                        'product_uom': wro_line.product_id.uom_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'lot_ids':[(6,0,lot_id.ids)]
                                    }))
                                picking_id = self.env['stock.picking'].sudo().create({
                                        'partner_id':self.merchand_id.id,
                                        'picking_type_id': picking_type_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'move_ids_without_package': line_ids,
                                        'origin': product_line.package_number,
                                        'wro_id':self.id,
                                        'owner_id':self.merchand_id.id
                                    })
                                picking_id.action_confirm()
                                for move_line in picking_id.move_line_ids_without_package:
                                    move_line.qty_done = move_line.product_uom_qty
                                    move_line.lot_id=lot_id.id
                                # picking_id.action_assign()
                                # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                                
                                lines = picking_id.mapped("move_line_ids").filtered(
                                    lambda x: (
                                        not x.lot_id
                                        and not x.lot_name
                                        and x.product_id.tracking != "none"
                                        
                                    )
                                )
                                lines.set_lot_auto(lot_id)
                                # for picking_line in picking_id.move_line_ids:
                                #     picking_line.write({'lot_id':lot_id.id})
                                if picking_id.state == 'draft':
                                    picking_id.action_confirm()
                                
                                #picking_id.button_validate()
                                picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
            else:
                for wro_line in self.wro_single_sku_per_pallet_ids:
                    if wro_line.consolidated_type == 'consolidated':
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                    
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            lot_id = self.env['stock.production.lot'].sudo().create({
                                'name':pallet_line.package_number,
                                'product_id':wro_line.product_id.id,
                                'company_id':self.company_id.id,
                                'product_qty':wro_line.qty_per_pallet
                                })
                            line_ids = []
                            line_ids.append((0,0,{
                                    'product_id': wro_line.product_id.id,
                                    'name': wro_line.product_id.display_name,
                                    'product_uom_qty': wro_line.qty_per_pallet,
                                    'product_uom': wro_line.product_id.uom_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': pallet_line.location_id.id,
                                    'lot_ids':[(6,0,lot_id.ids)]
                                }))
                            picking_id = self.env['stock.picking'].sudo().create({
                                    'partner_id':self.merchand_id.id,
                                    'picking_type_id': picking_type_id.id,
                                    'location_id': picking_type_id.default_location_src_id.id,
                                    'location_dest_id': pallet_line.location_id.id,
                                    'move_ids_without_package': line_ids,
                                    'origin': pallet_line.package_number,
                                    'wro_id':self.id,
                                    'owner_id':self.merchand_id.id
                                })
                            picking_id.action_confirm()
                            for move_line in picking_id.move_line_ids_without_package:
                                move_line.qty_done = move_line.product_uom_qty
                                move_line.lot_id=lot_id.id
                            # picking_id.action_assign()
                            # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
                            lines = picking_id.mapped("move_line_ids").filtered(
                                lambda x: (
                                    not x.lot_id
                                    and not x.lot_name
                                    and x.product_id.tracking != "none"
                                    
                                )
                            )
                            lines.set_lot_auto(lot_id)
                            # for picking_line in picking_id.move_line_ids:
                            #     picking_line.write({'lot_id':lot_id.id})
                            if picking_id.state == 'draft':
                                picking_id.action_confirm()
                            
                            #picking_id.button_validate()
                            picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
                    else:
                        line_ids = []
                        validate=False
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
                            if validate:
                                break
                            if not pallet_line.is_validated:
                                raise ValidationError("Please Validate All Box First")
                                break
                            for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
                                if not product_line.is_validated:
                                    raise ValidationError("Please Validate All Box First")
                                    break
                                    validate=True
                        for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:

                            for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
                                lot_id = self.env['stock.production.lot'].sudo().create({
                                        'name':product_line.package_number,
                                        'product_id':wro_line.product_id.id,
                                        'company_id':self.company_id.id,
                                        'product_qty':1
                                        })
                                line_ids = []
                                line_ids.append((0,0,{
                                        'product_id': wro_line.product_id.id,
                                        'name': wro_line.product_id.display_name,
                                        'product_uom_qty': 1,
                                        'product_uom': wro_line.product_id.uom_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'lot_ids':[(6,0,lot_id.ids)]
                                    }))
                                picking_id = self.env['stock.picking'].sudo().create({
                                        'partner_id':self.merchand_id.id,
                                        'picking_type_id': picking_type_id.id,
                                        'location_id': picking_type_id.default_location_src_id.id,
                                        'location_dest_id': product_line.location_id.id,
                                        'move_ids_without_package': line_ids,
                                        'origin': product_line.package_number,
                                        'wro_id':self.id,
                                        'owner_id':self.merchand_id.id
                                    })
                                picking_id.action_confirm()
                                for move_line in picking_id.move_line_ids_without_package:
                                    move_line.qty_done = move_line.product_uom_qty
                                    move_line.lot_id=lot_id.id
                                # picking_id.action_assign()
                                # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                                
                                lines = picking_id.mapped("move_line_ids").filtered(
                                    lambda x: (
                                        not x.lot_id
                                        and not x.lot_name
                                        and x.product_id.tracking != "none"
                                        
                                    )
                                )
                                lines.set_lot_auto(lot_id)
                                # for picking_line in picking_id.move_line_ids:
                                #     picking_line.write({'lot_id':lot_id.id})
                                if picking_id.state == 'draft':
                                    picking_id.action_confirm()
                                
                                #picking_id.button_validate()
                                picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
                storage_line_env = self.env['storage.type.line'].sudo()
                for line in wro_line.wro_single_sku_per_pallet_line_ids:
                    if line.send_as == "consolidated":
                        if line.location_id.storage_type_id:
                            billing_type = self.merchand_id.billing_type
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
                                billing_type = self.merchand_id.billing_type
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

                next_billing_date = fields.Date.today() + DT.timedelta(days=self.merchand_id.billing_type.days)
                self.last_billing_date = next_billing_date
                if len(order_line)>0:
                    SaleOrder=self.env['sale.order'].sudo()
                    sale_order = SaleOrder.create({
                            'partner_id': self.merchand_id.id,
                            'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                            'wro_id':self.id,
                            'note':'Billing -- '+self.name,
                            'order_line':order_line
                            #'team_id': team.id if team else False,
                        })
                    email_act = sale_order.action_quotation_send()
                    email_ctx = email_act.get('context', {})
                    sale_order.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
                    if self.merchand_id.merchant_billing_method=='prepaid':
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



        # else:
        #     if self.shipping_type =='parcel':
                
        #         for wro_line in self.wro_single_sku_per_box_ids:
        #             line_ids = []
        #             validate=False
        #             for box_line in wro_line.wro_single_sku_per_box_line_ids:
        #                 if validate:
        #                     break
        #                 if not box_line.is_validated:
        #                     raise ValidationError("Please Validate All Box First")
        #                     break
        #                 for product_line in box_line.wro_single_sku_per_box_product_line_ids:
        #                     if not product_line.is_validated:
        #                         raise ValidationError("Please Validate All Box First")
        #                         break
        #                         validate=True

        #         for wro_line in self.wro_single_sku_per_box_ids:
                    
        #             for box_line in wro_line.wro_single_sku_per_box_line_ids:
        #                 for product_line in box_line.wro_single_sku_per_box_product_line_ids:
        #                     lot_id = self.env['stock.production.lot'].sudo().create({
        #                             'name':product_line.package_number,
        #                             'product_id':wro_line.product_id.id,
        #                             'company_id':self.company_id.id,
        #                             'product_qty':1
        #                             })
        #                     line_ids = []
        #                     line_ids.append((0,0,{
        #                             'product_id': wro_line.product_id.id,
        #                             'name': wro_line.product_id.display_name,
        #                             'product_uom_qty': 1,
        #                             'product_uom': wro_line.product_id.uom_id.id,
        #                             'location_id': picking_type_id.default_location_src_id.id,
        #                             'location_dest_id': product_line.location_id.id,
        #                             'lot_ids':[(6,0,lot_id.ids)]
        #                         }))
        #                     picking_id = self.env['stock.picking'].sudo().create({
        #                             'partner_id':self.merchand_id.id,
        #                             'picking_type_id': picking_type_id.id,
        #                             'location_id': picking_type_id.default_location_src_id.id,
        #                             'location_dest_id': product_line.location_id.id,
        #                             'move_ids_without_package': line_ids,
        #                             'origin': product_line.package_number,
        #                             'wro_id':self.id,
        #                             'owner_id':self.merchand_id.id
        #                         })
        #                     picking_id.action_confirm()
        #                     for move_line in picking_id.move_line_ids_without_package:
        #                         move_line.qty_done = move_line.product_uom_qty
        #                         move_line.lot_id=lot_id.id
        #                     # picking_id.action_assign()
        #                     # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
        #                     lines = picking_id.mapped("move_line_ids").filtered(
        #                         lambda x: (
        #                             not x.lot_id
        #                             and not x.lot_name
        #                             and x.product_id.tracking != "none"
                                    
        #                         )
        #                     )
        #                     lines.set_lot_auto(lot_id)
        #                     # for picking_line in picking_id.move_line_ids:
        #                     #     picking_line.write({'lot_id':lot_id.id})
        #                     if picking_id.state == 'draft':
        #                         picking_id.action_confirm()
                            
        #                     #picking_id.button_validate()
        #                     picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
        #     else:
        #         for wro_line in self.wro_single_sku_per_pallet_ids:
        #             line_ids = []
        #             validate=False
        #             for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
        #                 if validate:
        #                     break
        #                 if not pallet_line.is_validated:
        #                     raise ValidationError("Please Validate All Box First")
        #                     break
        #                 for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
        #                     if not product_line.is_validated:
        #                         raise ValidationError("Please Validate All Box First")
        #                         break
        #                         validate=True
        #         for wro_line in self.wro_single_sku_per_pallet_ids:
                    
        #             for pallet_line in wro_line.wro_single_sku_per_pallet_line_ids:
        #                 for product_line in pallet_line.wro_single_sku_per_pallet_product_line_ids:
        #                     lot_id = self.env['stock.production.lot'].sudo().create({
        #                             'name':product_line.package_number,
        #                             'product_id':wro_line.product_id.id,
        #                             'company_id':self.company_id.id,
        #                             'product_qty':1
        #                             })
        #                     line_ids = []
        #                     line_ids.append((0,0,{
        #                             'product_id': wro_line.product_id.id,
        #                             'name': wro_line.product_id.display_name,
        #                             'product_uom_qty': 1,
        #                             'product_uom': wro_line.product_id.uom_id.id,
        #                             'location_id': picking_type_id.default_location_src_id.id,
        #                             'location_dest_id': product_line.location_id.id,
        #                             'lot_ids':[(6,0,lot_id.ids)]
        #                         }))
        #                     picking_id = self.env['stock.picking'].sudo().create({
        #                             'partner_id':self.merchand_id.id,
        #                             'picking_type_id': picking_type_id.id,
        #                             'location_id': picking_type_id.default_location_src_id.id,
        #                             'location_dest_id': product_line.location_id.id,
        #                             'move_ids_without_package': line_ids,
        #                             'origin': product_line.package_number,
        #                             'wro_id':self.id,
        #                             'owner_id':self.merchand_id.id
        #                         })
        #                     picking_id.action_confirm()
        #                     for move_line in picking_id.move_line_ids_without_package:
        #                         move_line.qty_done = move_line.product_uom_qty
        #                         move_line.lot_id=lot_id.id
        #                     # picking_id.action_assign()
        #                     # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
                            
        #                     lines = picking_id.mapped("move_line_ids").filtered(
        #                         lambda x: (
        #                             not x.lot_id
        #                             and not x.lot_name
        #                             and x.product_id.tracking != "none"
                                    
        #                         )
        #                     )
        #                     lines.set_lot_auto(lot_id)
        #                     # for picking_line in picking_id.move_line_ids:
        #                     #     picking_line.write({'lot_id':lot_id.id})
        #                     if picking_id.state == 'draft':
        #                         picking_id.action_confirm()
                            
        #                     #picking_id.button_validate()
        #                     picking_id.with_context(skip_immediate=True,skip_sms=True).button_validate()
        
                
                            
            


    def action_submit_warehouse(self, warehouse, wroId):
        warehouse_id = self.env['stock.warehouse'].sudo().browse(int(warehouse[0]))
        if wroId[0]:
            wroId = self.sudo().browse(int(wroId[0]))
            wroId.update({
                    'warehouse_id' : warehouse_id.id
                })
        else:
            wroId = self.sudo().create({
                    'warehouse_id' : warehouse_id.id,
                    'merchand_id':self.env.user.partner_id.id
                })
        return wroId.id

    def action_submit_arrival_date(self, vals, wroId):
        warehouse_id = self.env['stock.warehouse'].sudo().browse(int(wroId[0]))
        if wroId[0]:
            wroId = self.sudo().browse(int(wroId[0]))
            wroId.update({
                    'pickup_method': vals[0]['pickup_method'], 
                    'contact_name': vals[0]['contact_name'], 
                    'picking_address': vals[0]['contact_address'], 
                    'email': vals[0]['contact_email'], 
                    'phone': vals[0]['contact_phone'], 
                    'courier_company_name': vals[0]['courier_company_name'], 
                    'tracking_number': vals[0]['tracking_number'],
                    'arrival_date' : vals[0]['arrival_date_th'] or vals[0]['arrival_date_occ'],
                })
        return wroId.id

    def action_update_wro_lines(self, data, wroId, product_ids):
        product_ids = [int(i) for i in product_ids[0]]
        wr_id = False
        if wroId[0]:
            wr_id = self.sudo().browse(int(wroId[0]))
            wro_line_lst = [] 
            for rec in data[0]:
                wro_line_id = wr_id.wro_line_ids.filtered(lambda x: x.product_id.id == rec['product_id'])
                if wro_line_id:
                    wro_line_id.sudo().update({
                            'product_qty' : rec['product_qty'],
                            'package_value' : rec['package_value']
                        })
                else:
                    wro_line_id = self.env['wro.lines'].sudo().create({
                            'product_id': rec['product_id'],
                            'product_qty' : rec['product_qty'],
                            'package_value' : rec['package_value'],
                            'wro_id': wr_id.id,
                        })
        for rec in wr_id.wro_line_ids:
            if rec.product_id.id not in product_ids:
                rec.sudo().unlink()
        return wr_id.id

    def get_saved_product(self, wroId):
        product_ids = []
        if wroId[0]:
            wroId = self.sudo().browse(int(wroId[0]))
            for rec in wroId.wro_line_ids:
                vals = {
                    'product_id': rec.product_id.id,
                    'product_qty': int(rec.product_qty),
                }
                product_ids.append(vals)
        return product_ids

    def action_update_shipping_type(self, wroId, shipping_type, inventory_type):
        if wroId[0]:
            wroId = self.sudo().browse(int(wroId[0]))
            wroId.shipping_type = shipping_type[0]
            if wroId.shipping_type == 'parcel':
                wroId.wro_single_sku_per_pallet_ids.unlink()
                wroId.inventory_type_parcel = inventory_type[0]
                wroId.inventory_type_pallet = False
                for line in wroId.wro_line_ids:
                    wro_single_sku_per_box_id = self.env['wro.single.sku.per.box'].search([('product_id', '=', line.product_id.id), ('wro_id', '=', wroId.id)]) 
                    if not wro_single_sku_per_box_id:
                        wro_single_sku_per_box_id = self.env['wro.single.sku.per.box'].create({
                            'wro_id': wroId.id,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'package_value': line.package_value,
                        })
                    else:
                        wro_single_sku_per_box_id.update({
                            'product_qty': line.product_qty,
                            'package_value': line.package_value,
                        })
            if wroId.shipping_type == 'pallet':
                wroId.wro_single_sku_per_box_ids.unlink()
                wroId.inventory_type_pallet = inventory_type[0]
                wroId.inventory_type_parcel = False
                for line in wroId.wro_line_ids:
                    wro_single_sku_per_pallet_id = self.env['wro.single.sku.per.pallet'].search([('product_id', '=', line.product_id.id), ('wro_id', '=', wroId.id)]) 
                    if not wro_single_sku_per_pallet_id:
                        wro_single_sku_per_pallet_id = self.env['wro.single.sku.per.pallet'].create({
                            'wro_id': wroId.id,
                            'product_id': line.product_id.id,
                            'product_qty': line.product_qty,
                            'package_value': line.package_value,
                        })
                    else:
                        wro_single_sku_per_pallet_id.update({
                            'product_qty': line.product_qty,
                            'package_value': line.package_value,
                        })

        return

    def action_update_shipment_qty(self, data, wroId):
        if wroId[0]:
            
            wroId = self.sudo().browse(int(wroId[0]))
            if wroId.shipping_type == 'parcel':
                if wroId.inventory_type_parcel == 'single':
                    total_amount=0
                    for rec in data[0]:
                        box_size = self.env['box.size'].sudo().browse(int(rec['box_size']))
                        box_size_template =False
                        if wroId.merchand_id.billing_type:
                            for rec in wroId.merchand_id.billing_type.box_template_ids:
                                if rec.box_type_id.id==box_size.id:
                                    box_size_template=rec.id
                                    break

                        if box_size:
                            total_amount+=box_size.price if not box_size_template else box_size_template.price
                    if self.env.user.partner_id.merchant_billing_method=='credit':
                        partner_available_limit = self.env['sale.order'].sudo().check_customer_limit(self.env.user.partner_id)
                        if partner_available_limit<total_amount:
                            msg = 'Your available credit limit' \
                                  ' Amount = %s \nCheck "%s" Accounts or Credit ' \
                                  'Limits.' % (partner_available_limit,
                                               self.env.user.partner_id.name)
                            raise ValidationError(_(msg))
                    else:
                        if self.env.user.partner_id.wallet_balance<total_amount:
                            msg="Wallet balannce is low please topup to proceed"

                            raise ValidationError(_(msg))
                        

                    for rec in data[0]:
                        wro_single_sku_per_box_id = self.env['wro.single.sku.per.box'].browse(rec['line_id'])
                        if wro_single_sku_per_box_id:
                            wro_single_sku_per_box_id.write({
                                    'qty_per_box': rec['qty_per_box'],
                                    'no_of_boxes': rec['no_of_boxes'],
                                    'box_size': rec['box_size'],
                                    'consolidated_type':rec['consolidated_type'],
                                    'wro_single_sku_per_box_line_ids':[(6,0,[])]
                                })
                        iteration_time = 0
                        box_line_count = self.env['single.sku.per.box.line'].sudo().search_count([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)])
                        if not box_line_count:
                            iteration_time = int(wro_single_sku_per_box_id.no_of_boxes)
                        elif box_line_count < wro_single_sku_per_box_id.no_of_boxes:
                            iteration_time = wro_single_sku_per_box_id.no_of_boxes - box_line_count
                        elif box_line_count > wro_single_sku_per_box_id.no_of_boxes:
                            iteration_time = box_line_count - wro_single_sku_per_box_id.no_of_boxes
                            self.env['single.sku.per.box.line'].sudo().search([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)], limit=iteration_time, order='package_number desc').unlink()
                            iteration_time = 0
                        for i in range(0, int(iteration_time)):
                            # self.env['single.sku.per.box.line'].sudo().search([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)]).unlink()
                            box_line_id = self.env['single.sku.per.box.line'].sudo().create({
                                    'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.box.line'),
                                    'wro_single_sku_per_box_id': wro_single_sku_per_box_id.id,
                                    'send_as':rec['consolidated_type']
                                })
                            if rec['consolidated_type']=='non_consolidated':
                                for j in range(0,int(rec['qty_per_box'])):
                                    box_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                        'package_number': box_line_id.package_number+'/'+str(j+1),
                                        'wro_single_sku_per_box_line_id': box_line_id.id,
                                        
                                    })



            if wroId.shipping_type == 'pallet':
                if wroId.inventory_type_pallet == 'single':
                    for rec in data[0]:
                        wro_single_sku_per_pallet_id = self.env['wro.single.sku.per.pallet'].browse(rec['line_id'])
                        if wro_single_sku_per_pallet_id:
                            wro_single_sku_per_pallet_id.write({
                                    'qty_per_pallet': rec['qty_per_pallet'],
                                    'no_of_pallets': rec['no_of_pallets'],
                                    'consolidated_type':rec['consolidated_type'],
                                    'wro_single_sku_per_pallet_line_ids':[(6,0,[])]
                                })
                        iteration_time = 0
                        pallet_line_count = self.env['single.sku.per.pallet.line'].sudo().search_count([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)])
                        if not pallet_line_count:
                            iteration_time = int(wro_single_sku_per_pallet_id.no_of_pallets)
                        elif pallet_line_count < wro_single_sku_per_pallet_id.no_of_pallets:
                            iteration_time = wro_single_sku_per_pallet_id.no_of_pallets - pallet_line_count
                        elif pallet_line_count > wro_single_sku_per_pallet_id.no_of_pallets:
                            iteration_time = pallet_line_count - wro_single_sku_per_pallet_id.no_of_pallets
                            self.env['single.sku.per.pallet.line'].sudo().search([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)], limit=iteration_time, order='package_number desc').unlink()
                            iteration_time = 0
                        for i in range(0, int(iteration_time)):
                            # self.env['single.sku.per.pallet.line'].sudo().search([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)]).unlink()
                            pallet_line_id=self.env['single.sku.per.pallet.line'].sudo().create({
                                    'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.pallet.line'),
                                    'wro_single_sku_per_pallet_id': wro_single_sku_per_pallet_id.id,
                                    'send_as':rec['consolidated_type']
                                })
                            if rec['consolidated_type']=='non_consolidated':
                                for j in range(0,int(rec['qty_per_pallet'])):
                                    pallet_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                        'package_number': pallet_line_id.package_number+'/'+str(j+1),
                                        'wro_single_sku_per_pallet_line_id': pallet_line_id.id,
                                        
                                    })
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url+"/send/inventory/portal/"+str(wroId[0].id)+"?next=1"
        return url

    def action_print_grn_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('RETURNS')

        # Define some formats
        bold = workbook.add_format({'bold': True})
        border = workbook.add_format({'border': 1})
        center_align = workbook.add_format({'align': 'center', 'border': 1})
        right_align = workbook.add_format({'align': 'right', 'border': 1})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#FFFF00'})
        merge_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 14})
        box_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9EAD3'})

        # Fetch the company logo from the company's form field
        company = self.env.user.company_id
        if company.logo:
            try:
                # Decode the base64 image data
                logo_image_data = base64.b64decode(company.logo)
                logo_image_stream = io.BytesIO(logo_image_data)
                # Insert the logo into the worksheet
                worksheet.insert_image('B2', 'logo.png', {'image_data': logo_image_stream, 'x_scale': 0.4, 'y_scale': 0.4})
            except Exception as e:
                # Log the error if image insertion fails
                _logger.error("Failed to insert logo image: %s", e)

        # Write report headers
        worksheet.merge_range('D5:H5', 'SUMMARY REPORT (%s)' %(dict(self._fields['status'].selection).get(self.status)), merge_format)
       # Write report headers inside a bordered box (adjusted to B6:B10)
        worksheet.merge_range('B7:C7', 'Report No. %s' %(self.name), box_format)
        worksheet.merge_range('B8:C8', 'Status: %s' %(dict(self._fields['status'].selection).get(self.status)), box_format)
        worksheet.merge_range('B9:C9', 'Date: %s' %(self.received_date if self.status == 'received' else self.stored_date), box_format)

        # Write carrier method and receiving date in a bordered box
        worksheet.merge_range('E7:H7', 'Carrier Method: %s' %(dict(self._fields['pickup_method'].selection).get(self.pickup_method)), box_format)
        worksheet.merge_range('E8:H8', 'Receiving Date: %s' %(self.received_date), box_format)

        # Write column headers
        worksheet.merge_range('B12:B13', 'SKU', header_format)
        worksheet.merge_range('C12:C13', 'PRODUCT NAME', header_format)
        worksheet.merge_range('D12:H12', 'QTY', header_format)
        worksheet.write('D13', 'EXPTD', header_format)
        worksheet.write('E13', 'RECVD', header_format)
        worksheet.write('F13', 'EXCESS', header_format)
        worksheet.write('G13', 'RECVD NOT COMPLT', header_format)
        worksheet.write('H13', 'DAMGD', header_format)
        worksheet.merge_range('I12:I13', 'STATUS', header_format)

        # Write data rows
        row = 13
        data_lines = False
        carton_received = 0
        picking_ids = self.env['stock.picking'].sudo().search([('wro_id', '=', self.id)])
        total_received_qty = sum(picking_ids.move_ids_without_package.mapped('quantity_done'))
        if self.shipping_type == 'parcel':
            data_lines = self.wro_single_sku_per_box_ids
            carton_received = sum(data_lines.mapped('no_of_boxes'))
        if self.shipping_type == 'pallet':
            data_lines = self.wro_single_sku_per_pallet_ids
            carton_received = sum(data_lines.mapped('no_of_pallets'))
        for line in data_lines:
            worksheet.write(row, 1, line.product_id.default_code, border)
            worksheet.write(row, 2, line.product_id.name, right_align)
            worksheet.write_number(row, 3, float(line.product_qty), right_align)
            received_qty = 0
            if picking_ids:
                move_ids = picking_ids.move_ids_without_package.filtered(lambda x: x.product_id.id == line.product_id.id)
                received_qty = sum(move_ids.mapped('quantity_done'))
            worksheet.write_number(row, 4, float(received_qty), right_align)
            worksheet.write_number(row, 5, 0, right_align)
            worksheet.write_number(row, 6, 0, center_align)
            worksheet.write_number(row, 7, 0, center_align)
            worksheet.write(row, 8, '', center_align)
            row += 1
        


        # Add a summary row to calculate the sum of quantities
        sum_row = row
        worksheet.write(sum_row, 2, 'Total', total_format)
        worksheet.write_formula(sum_row, 3, f'=SUM(D14:D{sum_row})', total_format)
        worksheet.write_formula(sum_row, 4, f'=SUM(E14:E{sum_row})', total_format)
        worksheet.write_formula(sum_row, 5, f'=SUM(F14:F{sum_row})', total_format)
        worksheet.write_formula(sum_row, 6, f'=SUM(G14:G{sum_row})', total_format)
        worksheet.write_formula(sum_row, 7, f'=SUM(H14:H{sum_row})', total_format)

        # Write the summary table
        summary_data = [
            ('Qty On Packing list', sum(data_lines.mapped('product_qty'))),
            ('Qty received', total_received_qty),
            ('Shortages', 0),
            ('Excess', 0),
            ('Carton Received', carton_received),
            ('Damaged Carton Qty', 0),
        ]

        worksheet.merge_range('L12:M12', 'SUMMARY', header_format)
        worksheet.write('L13', self.name, header_format)
        worksheet.write('M13', 'QUANTITY', header_format)

        summary_row = 13
        for summary in summary_data:
            worksheet.write(summary_row, 11, summary[0], border)
            worksheet.write_number(summary_row, 12, summary[1], right_align)
            summary_row += 1

        # Close the workbook
        workbook.close()

        # Get the content of the Excel file
        output.seek(0)
        excel_file_content = output.read()
        output.close()
        # Encode the content into base64
        encoded_file_content = base64.b64encode(excel_file_content)

        attachment = self.env['ir.attachment'].sudo().search([('description', '=', 'WROGRNXLS')])
        if attachment:
            attachment.unlink()
        # Create an attachment to store the Excel file
        attachment = self.env['ir.attachment'].create({
            'name': '%s.xlsx' %(self.name),
            'type': 'binary',
            'datas': encoded_file_content,
            'store_fname': '%s.xlsx' %(self.name),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'description': 'WROGRNXLS'
        })

        # Return the URL to download the attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

        # # Return the Excel file as an HTTP response
        # output.seek(0)
        # response = self.env['ir.actions.report']._get_binary_files(
        #     name='%s.xlsx' %(self.name),
        #     data=output.read(),
        #     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        # )
        # return response

class WroLines(models.Model):
    _name = "wro.lines"
    _description = "WRO Lines"

    wro_id = fields.Many2one("warehouse.receive.order", string="WRO")
    product_id = fields.Many2one("product.product", string="Product",domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id)]")

    product_sku = fields.Char("SKU", related="product_id.default_code")
    platform = fields.Char("Platform", related="product_id.platform")
    product_qty = fields.Float("Quantity")
    package_value = fields.Float("Package Value")
    merchand_id = fields.Many2one(related="wro_id.merchand_id")


    
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     print("sssssssssssssssss")
    #     domain={'product_id': [('responsible_id', '=', self.wro_id.merchand_id.id)]}
    #     print(domain)
    #     return {'domain': {'product_id': [('responsible_id', '=', self.wro_id.merchand_id.id)]}}



    def get_consolated_type(self):
        wro_single_sku_per_box_id = self.env['wro.single.sku.per.box'].search([('product_id', '=', self.product_id.id), ('wro_id', '=', self.wro_id.id)])
        #print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
        return wro_single_sku_per_box_id.consolidated_type

    # def get_report_url(self, product_id):
    #     if self.shipping_type == 'parcel':
    #         wro_single_sku_per_box_id = self.env['wro.single.sku.per.box'].search([('product_id', '=', product_id), ('wro_id', '=', self.id)])
    #         print("**********", wro_single_sku_per_box_id)
    #         ee
    #         if wro_single_sku_per_box_id:
    #             return wro_single_sku_per_box_id.get_portal_url(report_type='pdf', download=True)
    #     if self.shipping_type == 'pallet':
    #         wro_single_sku_per_pallet_id = self.env['wro.single.sku.per.pallet'].search([('product_id', '=', product_id), ('wro_id', '=', self.id)]) 
    #         if wro_single_sku_per_pallet_id:
    #             return wro_single_sku_per_pallet_id.get_portal_url(report_type='pdf', download=True)
    #     return "#"

class WroSingleSkuPerBox(models.Model):
    _name = "wro.single.sku.per.box"
    _inherit = ['portal.mixin']
    _description = "WRO Single SKU Per Box"

    wro_id = fields.Many2one("warehouse.receive.order", string="WRO")
    merchand_id = fields.Many2one(related="wro_id.merchand_id")

    product_id = fields.Many2one("product.product", string="Item Information")
    product_qty = fields.Integer("Shipment Quantity")
    qty_per_box = fields.Integer("Quantity/Box")
    no_of_boxes = fields.Integer("#Of Boxes")
    subtotal_qty = fields.Integer("Total Quantity")
    package_value = fields.Float("Package Value")
    box_size = fields.Many2one('box.size', string="Type of Box",domain="[('type','=','box')]")
    wro_single_sku_per_box_line_ids = fields.One2many("single.sku.per.box.line", "wro_single_sku_per_box_id", string="Wro Single Sku Per Box Lines", copy=False)
    consolidated_type = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Consolidated Type", copy=False)
    location_label = fields.Char('Location Label')
    scan_package_number = fields.Char("Scanned package Number")
    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    # packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
    #                                 ('Flyer Size', 'Flyer Size'),
    #                                 ('Pallet', 'Pallet')], string="Packing category")
    is_package_required = fields.Boolean("Is Package Require")
    packing_type_id = fields.Many2one('thehub.packing.type')
    location_name = fields.Char('Cascading Location Name')
    is_default_location = fields.Boolean('default Location')
    defaultlocation_id = fields.Many2one("stock.location", string="Location", copy=False,domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id), ('location_full','!=',True)]")




    def cascade_lines(self):
        for rec in self.wro_single_sku_per_box_line_ids:
            if rec.is_selected and not rec.is_validated:
                rec.location_label=self.location_name

        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    


    def select_all_line(self):
        for rec in self.wro_single_sku_per_box_line_ids:
            rec.is_selected=True

        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }


    def action_validate_lines(self):
        for rec in self.wro_single_sku_per_box_line_ids:
            if rec.is_selected and not rec.is_validated:
                rec.is_selected=False
                rec.validate()
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                } 

    @api.onchange('product_qty')
    def _onchange_quantity(self):
        if self.product_qty>0:
            self.no_of_boxes=self.product_qty
            self.qty_per_box=1
        else:
            self.qty_per_box=0
            self.no_of_boxes=0


    @api.onchange('no_of_boxes')
    def _onchange_no_of_boxes(self):
        if self.product_qty>0 and self.no_of_boxes>0:
            self.qty_per_box=self.product_qty/self.no_of_boxes
            
        else:
            self.qty_per_box=0
            self.no_of_boxes=0


    @api.onchange('qty_per_box')
    def _onchange_qty_per_box(self):
        if self.product_qty>0 and self.qty_per_box>0:
            self.no_of_boxes=self.product_qty/self.qty_per_box
            
        else:
            self.qty_per_box=0
            self.no_of_boxes=0    


    def add_packaging_cost(self):
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_box_id':self.id,'default_packing_categ':'Carton Sizes','default_is_package':True}
                }

    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            for rec in self.wro_id:
                record.show_received_done_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_received_done_btn = True
    

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for record in self:
            for rec in self.wro_id:
                record.show_picker_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_picker_btn = True
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.wro_id.name)


    def edit_quantity(self):
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_box_id':self.id}
                }


    def validate_lines(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    def print_labels(self):
        target_url =  self.sudo().env['ir.config_parameter'].get_param('web.base.url') +"/print/duplicate/box/label/"+str(self.id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'state': self.id,
            'url': target_url
        }




    def create_picker_activity(self):
        user_ids = self.env.company.sudo().wro_picker_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'warehouse.receive.order'),
                ('res_id', 'in', self.wro_id.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.wro_id.sudo().activity_schedule('ag_the_hub.mail_activity_picker_process_wro', user_id=user_id.id)
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    def action_report_discrepancy(self):
        pass


        




        



class WroSingleSkuPerBoxLine(models.Model):
    _name = "single.sku.per.box.line"
    _description = "Wro Single Sku Per Box Line"

    package_number = fields.Char("Package Number")
    send_as = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Send As", default="consolidated")
    merchand_id = fields.Many2one('res.partner',compute="_compute_merchant_id",store=True)
    wro_single_sku_per_box_id = fields.Many2one("wro.single.sku.per.box", string="WRO Single SKU Per Box")
    product_id = fields.Many2one(related="wro_single_sku_per_box_id.product_id",store=True, string="Item Information")
    location_id = fields.Many2one("stock.location", string="Storage Location", copy=False,domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id), ('location_full','!=',True)]")
    location_label = fields.Char('Location Label')
    scan_package_number = fields.Char("Scanned package Number")
    wro_single_sku_per_box_product_line_ids = fields.One2many("single.sku.per.box.product.line", "wro_single_sku_per_box_line_id", string="Wro Single Sku Per Box Product Lines", copy=False)
    is_validated = fields.Boolean()
    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    is_package_required = fields.Boolean("Is Package Require")
    packing_type_id = fields.Many2one('thehub.packing.type')

    location_name = fields.Char("Location name")
    is_selected = fields.Boolean("Select")

    @api.depends('wro_single_sku_per_box_id','wro_single_sku_per_box_id.wro_id.merchand_id')
    def _compute_merchant_id(self):
        #print("11111111111111111111111111")
        for rec in self:
            if rec.wro_single_sku_per_box_id.wro_id and rec.wro_single_sku_per_box_id.wro_id.merchand_id.billing_type.storage_type == 'Dedicated':
                rec.merchand_id=rec.wro_single_sku_per_box_id.wro_id.merchand_id.id





    def action_go_back(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_box_id.id,
                }

    def action_select_all_lines(self):
        for line in self.wro_single_sku_per_box_product_line_ids:
            #if line.is_selected:
            line.is_selected=True


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.box.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }



    def action_validate_lines(self):
        for line in self.wro_single_sku_per_box_product_line_ids:
            if line.is_selected and not  line.is_validated:
                line.validate()
                line.is_selected=False


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.box.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    def action_update_location_label(self):
        for line in self.wro_single_sku_per_box_product_line_ids:
            if line.is_selected:
                line.location_label=self.location_name
                line.is_selected=False


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.box.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }



    



    def add_packaging_cost(self):
        #print("333333333333333333333333333333333333333333")
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_box_line_id':self.id,'default_packing_categ':'Carton Sizes','default_is_package':True}
                }



    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            for rec in self.wro_single_sku_per_box_id.wro_id:
                record.show_received_done_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_received_done_btn = True
    

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for record in self:
            for rec in self.wro_single_sku_per_box_id.wro_id:
                record.show_picker_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_picker_btn = True


    # def create_picker_activity(self):
    #     user_ids = self.env.company.sudo().wro_picker_user_ids
    #     for user_id in user_ids:
    #         domain = [
    #             ('res_model', '=', 'warehouse.receive.order'),
    #             ('res_id', 'in', self.wro_id.ids),
    #             ('user_id', '=', user_id.id),
    #             ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
    #         ]
    #         activities = self.env['mail.activity'].sudo().search(domain)
    #         if not activities:
    #             self.wro_id.sudo().activity_schedule('ag_the_hub.mail_activity_picker_process_wro', user_id=user_id.id)
    #     return {'type': 'ir.actions.act_window',
    #             'res_model': 'wro.single.sku.per.box',
    #             'view_mode': 'form',
    #             'target': 'new',
    #             'res_id':self.id,
    #             }
    



    
    



    def validate(self):
        picking_type_id = self._get_picking_type(self.wro_single_sku_per_box_id.wro_id.company_id.id)
        

        if self.send_as == 'non_consolidated':
            for rec in self.wro_single_sku_per_box_product_line_ids:
                if not rec.is_validated:
                    raise ValidationError(_('Please check location and location_label and package_number'))
                    break
                self.is_validated=True

            return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_box_id.id,
                }
        else:
            if not self.location_id or not self.location_label or not self.scan_package_number:
                raise ValidationError(_('Please check location and location_label and package_number'))
            if self.scan_package_number != self.package_number:
                raise ValidationError(_('Paclage Number not matched please check'))
            if self.location_id.location_scan_name != self.location_label:
                raise ValidationError(_('location not matched please check'))
            self.is_validated=True
            return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_box_id.id,
                }


    def action_open_view(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.box.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }










    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]




class WroSingleSkuPerBoxProductLine(models.Model):
    _name = "single.sku.per.box.product.line"
    _description = "Wro Single Sku Per Box Product Line"

    package_number = fields.Char("Package Number")
    send_as = fields.Selection(related="wro_single_sku_per_box_line_id.send_as", string="Send As" ,store=True)
    send_as_pallet = fields.Selection(related="wro_single_sku_per_pallet_line_id.send_as", string="Send As" ,store=True)
    wro_single_sku_per_box_line_id = fields.Many2one("single.sku.per.box.line", string="WRO Single SKU Per Box")
    location_id = fields.Many2one("stock.location", string="Storage Location", copy=False,domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id), ('location_full','!=',True)]")
    merchand_id = fields.Many2one('res.partner',compute="_compute_merchant_id",store=True)
    is_selected = fields.Boolean("Select")
    
    location_label = fields.Char('Location Label')
    scan_package_number = fields.Char("Scanned package Number")
    is_validated = fields.Boolean('Validated')
    wro_single_sku_per_pallet_line_id = fields.Many2one("single.sku.per.pallet.line", string="WRO Single SKU Per Box")
    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    packing_type_id = fields.Many2one('thehub.packing.type')
    is_package_required = fields.Boolean("Is Package Require")
    
    


    def add_packaging_cost(self):
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_product_line_id':self.id,'default_packing_categ':'Carton Sizes','default_is_package':True}
                }

    @api.depends('wro_single_sku_per_box_line_id','wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id.merchand_id','wro_single_sku_per_pallet_line_id')
    def _compute_merchant_id(self):
        #print("11111111111111111111111111")
        for rec in self:
            if rec.wro_single_sku_per_box_line_id:
                if rec.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id and rec.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id.merchand_id.billing_type.storage_type == 'Dedicated':
                    rec.merchand_id=rec.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id.merchand_id.id
            elif rec.wro_single_sku_per_pallet_line_id:
                if rec.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id and rec.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id.merchand_id.billing_type.storage_type == 'Dedicated':
                    rec.merchand_id=rec.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id.merchand_id.id


    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            if record.wro_single_sku_per_box_line_id:
                for rec in record.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id:
                    record.show_received_done_btn = False
                    if current_user.id in user_ids.ids:
                        domain = [
                            ('res_model', '=', 'warehouse.receive.order'),
                            ('res_id', 'in', rec.ids),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            record.show_received_done_btn = True
            else:
                for rec in record.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id:
                    record.show_received_done_btn = False
                    if current_user.id in user_ids.ids:
                        domain = [
                            ('res_model', '=', 'warehouse.receive.order'),
                            ('res_id', 'in', rec.ids),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            record.show_received_done_btn = True

    

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for record in self:
            if record.wro_single_sku_per_box_line_id:
                for rec in record.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id:
                    record.show_picker_btn = False
                    if current_user.id in user_ids.ids:
                        domain = [
                            ('res_model', '=', 'warehouse.receive.order'),
                            ('res_id', 'in', rec.ids),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            record.show_picker_btn = True
            else:
                for rec in record.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id:

                    record.show_picker_btn = False
                    if current_user.id in user_ids.ids:
                        domain = [
                            ('res_model', '=', 'warehouse.receive.order'),
                            ('res_id', 'in', rec.ids),
                            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                        ]
                        activities = self.env['mail.activity'].sudo().search(domain)
                        if activities:
                            record.show_picker_btn = True


    


    def validate(self):
        if not self.location_id or not self.location_label or not self.scan_package_number:
            raise ValidationError(_('Please check location and location_label and package_number'))
        if self.scan_package_number != self.package_number:
            raise ValidationError(_('Paclage Number not matched please check'))
        if self.location_id.location_scan_name != self.location_label:
            raise ValidationError(_('location not matched please check'))
        

        self.is_validated=True

        if self.wro_single_sku_per_box_line_id:
            return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.box.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_box_line_id.id,
                }
        else:
            return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.pallet.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_pallet_line_id.id,
                }
    
    
    # def create(self, vals):
    #     res = super(WroSingleSkuPerBoxLine, self).create(vals)
    #     if not res.package_number:
    #         seq = self.env['ir.sequence'].sudo().next_by_code('single.sku.per.box.line')
    #         res.package_number = seq
    #     return res

class WroSingleSkuPerPallet(models.Model):
    _name = "wro.single.sku.per.pallet"
    _inherit = ['portal.mixin']
    _description = "WRO Single SKU Per Pallet"


    def _get_pallet_size(self):
        pallet_size_id = self.env['box.size'].sudo().search([('type','=','box')],limit=1)
        return pallet_size_id.id

    wro_id = fields.Many2one("warehouse.receive.order", string="WRO")
    merchand_id = fields.Many2one(related="wro_id.merchand_id")

    product_id = fields.Many2one("product.product", string="Item Information")
    product_qty = fields.Integer("Shipment Quantity")
    qty_per_pallet = fields.Integer("Quantity/Pallet")
    no_of_pallets = fields.Integer("#Of pallets")
    subtotal_qty = fields.Integer("Total Quantity")
    package_value = fields.Float("Package Value")
    consolidated_type = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Consolidated Type", copy=False)
    
    wro_single_sku_per_pallet_line_ids = fields.One2many("single.sku.per.pallet.line", "wro_single_sku_per_pallet_id", string="Wro Single Sku Per Pallet Lines", copy=False)

    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    pallet_size = fields.Many2one('box.size', string="Type of Pallet",default=_get_pallet_size)
    location_name = fields.Char('Cascading Location Name')
    is_default_location = fields.Boolean('default Location')
    defaultlocation_id = fields.Many2one("stock.location", string="Location", copy=False,domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id), ('location_full','!=',True)]")





    def cascade_lines(self):
        for rec in self.wro_single_sku_per_pallet_line_ids:
            if self.is_selected and not rec.is_validated:
                rec.location_label=self.location_name

        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    


    def select_all_line(self):
        for rec in self.wro_single_sku_per_pallet_line_ids:
            rec.is_selected=True

        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }


    def action_validate_lines(self):
        for rec in self.wro_single_sku_per_pallet_line_ids:
            if rec.is_selected and not rec.is_validated:
                rec.is_selected=False
                rec.validate()
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }

    @api.onchange('product_qty')
    def _onchange_quantity(self):
        if self.product_qty>0:
            self.no_of_pallets=self.product_qty
            self.qty_per_pallet=1
        else:
            self.qty_per_pallet=0
            self.no_of_pallets=0


    @api.onchange('no_of_pallets')
    def _onchange_no_of_pallets(self):
        if self.product_qty>0 and self.no_of_pallets>0:
            self.qty_per_pallet=self.product_qty/self.no_of_pallets
            
        else:
            self.qty_per_pallet=0
            self.no_of_pallets=0


    @api.onchange('qty_per_pallet')
    def _onchange_qty_per_pallet(self):
        if self.product_qty>0 and self.qty_per_pallet>0:
            self.no_of_pallets=self.product_qty/self.qty_per_pallet
            
        else:
            self.qty_per_pallet=0
            self.no_of_pallets=0

    


    



    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            for rec in self.wro_id:
                record.show_received_done_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_received_done_btn = True
    

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for record in self:
            for rec in self.wro_id:
                record.show_picker_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_picker_btn = True

    def create_picker_activity(self):
        user_ids = self.env.company.sudo().wro_picker_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'warehouse.receive.order'),
                ('res_id', 'in', self.wro_id.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.wro_id.sudo().activity_schedule('ag_the_hub.mail_activity_picker_process_wro', user_id=user_id.id)
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }
    
    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.wro_id.name)

    def edit_quantity(self):
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_pallet_id':self.id}
                }


    def validate_lines(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }
    def print_labels(self):
        target_url =  self.sudo().env['ir.config_parameter'].get_param('web.base.url') +"/print/duplicate/pallet/label/"+str(self.id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'state': self.id,
            'url': target_url
        }


class WroSingleSkuPerPalletLine(models.Model):
    _name = "single.sku.per.pallet.line"
    _description = "Wro Single Sku Per Pallet Line"

    package_number = fields.Char("Package Number")
    send_as = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Send As", default="consolidated")
    wro_single_sku_per_pallet_id = fields.Many2one("wro.single.sku.per.pallet", string="WRO Single SKU Per Pallet")
    #location_id = fields.Many2one("stock.location", string="Receiver Location", copy=False)
    location_id = fields.Many2one("stock.location", string="Receiver Location", copy=False,domain="['|', ('partner_id','=',merchand_id), ('partner_id.child_ids','in',merchand_id), ('location_full','!=',True)]")
    merchand_id = fields.Many2one('res.partner',compute="_compute_merchant_id",store=True)
    
    wro_single_sku_per_pallet_product_line_ids = fields.One2many("single.sku.per.box.product.line", "wro_single_sku_per_pallet_line_id", string="Wro Single Sku Per Box Product Lines", copy=False)
    location_label = fields.Char('Location Label')
    scan_package_number = fields.Char("Scanned package Number")
    is_validated = fields.Boolean('Validated')
    show_picker_btn = fields.Boolean(string="Show picker Button" ,compute='_compute_show_picker_btn')
    show_received_done_btn = fields.Boolean(string="Show Receive Done Button" ,compute='_compute_show_receive_done_btn')
    is_package_required = fields.Boolean("Is Package Require")
    packing_type_id = fields.Many2one('thehub.packing.type')
    location_name = fields.Char("Location name")
    is_selected = fields.Boolean("Select")



    def action_update_location_label(self):
        for line in self.wro_single_sku_per_pallet_product_line_ids:
            if line.is_selected and not line.is_validated:
                line.location_label=self.location_name
                line.is_selected=False


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.pallet.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }



    def action_select_all_lines(self):
        for line in self.wro_single_sku_per_pallet_product_line_ids:
            #if line.is_selected:
            line.is_selected=True


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.pallet.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }



    def action_validate_lines(self):
        for line in self.wro_single_sku_per_pallet_product_line_ids:
            if line.is_selected and not line.is_validated:
                line.validate()
                line.is_selected=False


        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.pallet.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }


    def action_go_back(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_pallet_id.id,
                }
    

    @api.depends('wro_single_sku_per_pallet_id','wro_single_sku_per_pallet_id.wro_id.merchand_id')
    def _compute_merchant_id(self):
        #print("11111111111111111111111111")
        for rec in self:
            if rec.wro_single_sku_per_pallet_id.wro_id and rec.wro_single_sku_per_pallet_id.wro_id.merchand_id.billing_type.storage_type == 'Dedicated':
                rec.merchand_id=rec.wro_single_sku_per_pallet_id.wro_id.merchand_id.id




    def add_packaging_cost(self):
        #print("33333333333333333>>>>>>>>>>")
        view = self.env.ref('ag_the_hub.view_update_quantoty_form')
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.update.quantity',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_product_per_box_id':self.id,'default_packing_categ':'Carton Sizes','default_is_package':True}
                }


    def _compute_show_receive_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            for rec in self.wro_single_sku_per_pallet_id.wro_id:
                record.show_received_done_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_submitted_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_received_done_btn = True
    

    def _compute_show_picker_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.wro_picker_user_ids
        for record in self:
            for rec in self.wro_single_sku_per_pallet_id.wro_id:
                record.show_picker_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'warehouse.receive.order'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_picker_process_wro').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_picker_btn = True



    def validate(self):
        #picking_type_id = self._get_picking_type(self.wro_single_sku_per_box_id.wro_id.company_id.id)
        

        if self.send_as == 'non_consolidated':
            for rec in self.wro_single_sku_per_pallet_product_line_ids:
                if not rec.is_validated:
                    raise ValidationError(_('Please check location and location_label and package_number'))
                    break
                self.is_validated=True

            return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_pallet_id.id,
                }
        else:
            if not self.location_id or not self.location_label or not self.scan_package_number:
                raise ValidationError(_('Please check location and location_label and package_number'))
            if self.scan_package_number != self.package_number:
                raise ValidationError(_('Paclage Number not matched please check'))
            if self.location_id.location_scan_name != self.location_label:
                raise ValidationError(_('location not matched please check'))
            self.is_validated=True
            return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.pallet',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.wro_single_sku_per_pallet_id.id,
                }


    def action_open_view(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'single.sku.per.pallet.line',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.id,
                }









    
    

    # def create(self, vals):
    #     res = super(WroSingleSkuPerPalletLine, self).create(vals)
    #     if not res.package_number:
    #         seq = self.env['ir.sequence'].sudo().next_by_code('single.sku.per.pallet.line')
    #         res.package_number = seq
    #     return res


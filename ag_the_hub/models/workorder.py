# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import xlwt
import io
import pytz
import calendar

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from dateutil.relativedelta import relativedelta


class Workorder(models.Model):
    _name = "thehub.workorder"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Workorder"
    _order = 'name desc'

    name = fields.Char("Name", copy=False)
    whom_to_ship = fields.Selection([('Business', 'Business'),
                                    ('Consumer', 'Consumer')], string="Whom to Ship?")
    partner_id = fields.Many2one("res.partner", string="Recipient",domain="[('merchant_partner_id','=',merchand_id)]")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self:self.env.company)
    merchand_id = fields.Many2one("res.partner",string="Merchant",domain="[('contact_type','=','Merchant')]")

    
    shipping_type = fields.Selection([('Parcel', 'Parcel'),
                                    ('Freight', 'Freight')], string="Shipping Type")
    payment_type = fields.Selection([('The Hub Buys', 'The Hub Buys'),
                                    ('My own 3PL Arrangement', 'My own 3PL Arrangement')], string="Payment Type")
    packaging_instructions = fields.Text("Packaging Instructions")

    wo_line_ids = fields.One2many("thehub.workorder.lines", "workorder_id", string="Workorder Lines", ondelete="cascade")
    wo_return_line_ids = fields.One2many("thehub.workorder.lines", "workorder_id", string="Workorder Lines", ondelete="cascade")
    wro_shipping_type = fields.Selection([('parcel', 'Parcel (standard shipping)'),
                                      ('pallet', 'Palletized container or LTL (less-than-truckload)'),
                                      ('container', 'Floor loaded container')], string="Shipping Type")
    
    
    status = fields.Selection([('Pending', 'Pending'),
                                ('Awaiting', 'Awaiting'),
                                ('Dispatched', 'Dispatched'),
                                ('Delivered', 'Delivered'),
                                ('Returned', 'Returned')
                                ], string="Status", default="Pending", copy=False)
    status_return = fields.Selection([('return_gen', 'RETURN ACTIVATED'),
                                ('return_rec', 'RETURN RECEIVED'),
                                ('return_done', 'RETURN STORED')],string='Status', default="return_gen", copy=False)
    show_picking_done_btn = fields.Boolean(string="Show Picking Done Button" ,compute='_compute_show_picking_done_btn')
    wo_picking_done = fields.Boolean("WO Picking Done", default=False, copy=False)
    show_packing_done_btn = fields.Boolean(string="Show Packing Done Button" ,compute='_compute_show_packing_done_btn')
    wo_packing_done = fields.Boolean("WO Packing Done", default=False, copy=False)
    show_dispatch_done_btn = fields.Boolean(string="Show Dispatch Done Button" ,compute='_compute_show_dispatch_done_btn')
    show_dispatch_not_done_btn = fields.Boolean(string="Show Dispatch Not Done Button" ,compute='_compute_show_dispatch_done_btn')
    wo_dispatch_date = fields.Date("Dispatched Date", copy=False)
    wo_dispatch_done = fields.Boolean("WO Dispatch Done", default=False, copy=False)
    wo_return_done = fields.Boolean("WO Return Done", default=False, copy=False)
    three_plcompany = fields.Many2one('thehub.3plcompanies')
    schedule_pickup = fields.Date('Schedule Date',tracking=True,)
    picking_count = fields.Char("Ticket",compute='_compute_picking_count')
    shipping_to = fields.Selection([('same_address', 'Same Package for Lines'),
                                    ('diff_addres', 'Different Package for Lines')], string="Shipping to",default='same_address')

    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")
    packing_type_id = fields.Many2one('thehub.packing.type',domain="[('packing_categ', '=', packing_categ),('packing_type','=','wo')]")
    dispute_raised = fields.Boolean()
    dispute_description = fields.Text("Dispute Description")
    show_receive_btn_done = fields.Boolean(string="Show Packing Done Button" ,compute='_compute_show_receive_btn_done')
    seal_number = fields.Char("Seal Number")
    
    # carton_packing  = fields.Selection([('Small', 'Small'),
    #                                 ('Medium', 'Medium'),
    #                                 ('Large', 'Large'),
    #                                 ('Custom', 'Custom')], string="Carton Packing Box")
    # flyer_packing  = fields.Selection([('Small', 'Small'),
    #                                 ('Medium', 'Medium'),
    #                                 ('Large', 'Large'),
    #                                 ('XLarge', 'XLarge')], string="Flyer Packing Box")
    wo_type  = fields.Selection([('delivery', 'Delivery'),
                                ('return', 'Return')
                                    ], string="Workorder Type",default='delivery')
    return_wo_id = fields.Many2one('thehub.workorder',string="Return Workorder",copy=False)
    delivered_date = fields.Date("Delivered Date",compute="_compute_delivered_date",store=True)
    sale_order_count = fields.Integer(compute="_compute_sale_order",string="Sale Order")
    package_lines = fields.One2many("thehub.workorder.lines.package","wo_id",string="Package Lines")
    third_party_ref = fields.Char("Third Party Ref #")
    date_create = fields.Date("Create Date", compute="_compute_date_create", store=True)

    @api.depends('create_date')
    def _compute_date_create(self):
        for rec in self:
            rec.date_create = rec.create_date.date()


    def action_open_line_list(self):
        domain = [('id', 'in', self.wo_line_ids.ids)]
            
        return {
            'name': _('WorkOrder Lines'),
            'view_mode': 'tree',
            'res_model': 'thehub.workorder.lines',
            'view_id': self.env.ref('ag_the_hub.thehub_workorder_lines_list_view').id,
            'domain': domain,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }



    def action_bulk_add_lines(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'name': _('Bulk Import Lines'),
            'res_model': 'bulk.import.lines',
             'target': 'new',
             'context':{'default_wo_id':self.id}
            
            
        }
        return action 



    def action_add_line(self):
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Line'),
            'res_model': 'wo.line.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wo_id': self.id,
                'default_is_manual':True if self.merchand_id.wo_stock_type=='manually' else False
            }
        }

    def action_delete_package(self):
        count=0
        for rec in self.package_lines:
            if rec.select:
                count=1
                rec.unlink()
        if count==0:
            raise UserError("Please select Package then delete")


    def action_scann_package_wizard(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'scanned.package.number',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_wo_id':self.id}
                }

    def action_scann_package_wizard_packages(self):
        return {'type': 'ir.actions.act_window',
                'res_model': 'scanned.package.number',
                'view_mode': 'form',
                'target': 'new',
                'context':{'default_wo_id':self.id,'default_is_packages':True}
                }

    def action_update_package(self):
        self.package_lines=False
        for line in self.wo_line_ids:
            self.env['thehub.workorder.lines.package'].sudo().create({
                    'packing_categ':self.packing_categ,
                    'packing_type_id':self.packing_type_id.id,
                    'product_lines':[(6,0,line.ids)],
                    'address':line.delivery_address,
                    'wo_id':self.id,
                    'weight':line.weight
                    })


    def action_add_package(self):
        # line_ids = self.wo_line_ids.mapped('id')
        
        # package_line_ids = []
        # for rec in self.package_lines:
        #     package_line_ids=package_line_ids+rec.product_lines.ids
        # difference = list(set(line_ids) - set(package_line_ids))
        # print("*******", difference)
        # ee
        # if len(difference)>0:
        #     record_list=[]
        #     for line_id in difference:
        #         record_list.append((0,0,{
        #             'wo_line':line_id
        #             }))


        return {'type': 'ir.actions.act_window',
            'res_model': 'add.packaging',
            'view_mode': 'form',
            'target': 'new',
            'context':{
                    # 'default_available_product_lines':record_list,
                    'default_wo_id':self.id
                }
            }




    def get_graph_data(self):
        Workorders = self.env['thehub.workorder'].sudo()
        domain = [('merchand_id', '=', self.env.user.partner_id.id)]
        data={}
        
        date = fields.Date.today()
        month_new=date.month
        year_new=date.month
        cm_wo_delivered_count = len(Workorders.search(domain + [('status', '=', 'Delivered')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wo_returned_count = len(Workorders.search(domain + [('status', '=', 'Returned')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wo_pending_count = len(Workorders.search(domain + [('status', '=', 'Pending')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wo_awaiting_count = len(Workorders.search(domain + [('status', '=', 'Awaiting')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        cm_wo_dispatch_count = len(Workorders.search(domain + [('status', '=', 'Dispatched')]).filtered(lambda x: x.create_date.month == month_new and x.create_date.year == year_new))
        

        wo_delivered_count = len(Workorders.search(domain + [('status', '=', 'Delivered')]))
        wo_returned_count = len(Workorders.search(domain + [('status', '=', 'Returned')]))
        wo_pending_count = len(Workorders.search(domain + [('status', '=', 'Pending')]))
        wo_awaiting_count = len(Workorders.search(domain + [('status', '=', 'Awaiting')]))
        wo_dispatch_count = len(Workorders.search(domain + [('status', '=', 'Dispatched')]))
        
        data={
        'list1':[cm_wo_pending_count,cm_wo_awaiting_count,cm_wo_returned_count,cm_wo_dispatch_count,cm_wo_delivered_count],
        'list2':[wo_pending_count,wo_awaiting_count,wo_returned_count,wo_dispatch_count,wo_delivered_count]
        }
        return data

    def delete_wo_list(self,data):
        return True

    def export_wo_list(self,data):
        IrConfig = self.env['ir.config_parameter'].sudo()

        base_url = IrConfig.get_param('web.base.url')
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('wo_status_report')
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(50 * 260)
        worksheet.col(5).width = int(18 * 260)
        worksheet.col(6).width = int(18 * 260)
        worksheet.col(7).width = int(18 * 260)

        row = 0
        worksheet.write_merge(row, row + 1, 0, 7, 'WRO Report', xlwt.easyxf('font:bold on;alignment: horizontal  center;'))
        row += 2
        row += 3

        worksheet.write(row, 3, 'SHIPPING ID', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 4, 'SHIP DATE', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 5, 'SHIPPING TYPE', xlwt.easyxf('font:bold on'))
        
        worksheet.write(row, 6, 'CUSTOMER', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 7, 'STATUS', xlwt.easyxf('font:bold on'))

        row += 1
        # total_qty=0
        # total_price=0
        wo_ids = self.env['thehub.workorder'].sudo().search([('id','in',data)])


        for line in wo_ids:
            worksheet.write(row, 3, line.name)
            worksheet.write(row, 4, str(line.create_date))
            worksheet.write(row, 5, str(line.shipping_type if line.shipping_type else ''))
            worksheet.write(row, 6, str(line.partner_id.name))
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
            rec.sale_order_count = self.env['sale.order'].sudo().search_count([('wo_id','=',rec.id)])
            

    def action_view_sale_order(self):
        sale_order_id = self.env['sale.order'].sudo().search([('wo_id','=',self.id)])  
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
    def _compute_delivered_date(self):
        for rec in self:
            if rec.status=='Delivered':
                rec.delivered_date=fields.Date.today()
    


    def action_open_return_order(self):


        return {
            'type': 'ir.actions.act_window',
            'res_model': 'thehub.workorder',
            'view_mode': 'form',
            'res_id': self.return_wo_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_receive_return(self):
        for line in self.wo_line_ids:
            if not line.is_validated:
                mag="Please verify  first line for "+line.package_number
                raise ValidationError(mag)
        for line in self.wo_line_ids:
            if line.return_stock_picking_id.state == 'draft':
                line.return_stock_picking_id.action_confirm()
            for move_line in line.return_stock_picking_id.move_line_ids_without_package:
                move_line.qty_done = move_line.product_uom_qty
                    
            line.return_stock_picking_id.with_context(skip_immediate=True,skip_backorder=True, skip_sms=True).button_validate()
        
        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_return_wo').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Return Done")
        self.status_return='return_done'



    def action_packing_verify(self):
        for line in self.wo_line_ids:
            if not line.source_location:
                mag="Please update Source Location in package "+line.package_number
                raise ValidationError(msg)
        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_return_process_pending_wo').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Return Package Verified")
        user_ids = self.env.company.picker_user_ids
        for user_id in user_ids:
            domain = [
                ('res_model', '=', 'thehub.workorder'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_return_wo').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.activity_schedule('ag_the_hub.mail_activity_process_return_wo', user_id=user_id.id)

        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', self.company_id.id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        picking_type_id=picking_type[:1]
        if picking_type_id.default_location_dest_id:
            location_dest_id = picking_type_id.default_location_dest_id.id
        
        workorder_line_rec = []
        
        for item in self.wo_line_ids:
            wo_line_dic = {}
            # rec = int(item.split('_')[2])
            #quant_id = request.env['stock.quant'].sudo().browse(item.package_id)
            #if kw.get('quantity_{}'.format(rec)):
            #     wo_line_dic.update({'product_qty': kw.pop('quantity_{}'.format(rec))})
            lot_id = self.env['stock.production.lot'].sudo().search([('name','=',item.stock_picking_id.origin)])
            if not lot_id:
                lot_id = self.env['stock.production.lot'].sudo().create({
                            'name':item.stock_picking_id.origin,
                            'product_id':item.product_id.id,
                            'company_id':self.company_id.id,
                            'product_qty':item.product_qty
                            })
            line_ids = []
            line_ids.append((0,0,{
                    'product_id': item.product_id.id,
                    'name': item.product_id.display_name,
                    'product_uom_qty': item.product_qty,
                    'product_uom': item.product_id.uom_id.id,
                    'location_id': item.stock_picking_id.location_dest_id.id,
                    'location_dest_id': item.source_location.id,
                    'lot_ids':[(6,0,lot_id.ids)]
                }))
            picking_id = self.env['stock.picking'].sudo().create({
                    'partner_id':self.merchand_id.id,
                    'picking_type_id': picking_type_id.id,
                    'location_id': item.stock_picking_id.location_dest_id.id,
                    'location_dest_id': item.source_location.id,
                    'move_ids_without_package': line_ids,
                    'origin': item.stock_picking_id.origin,
                    'wo_id':self.id,
                    'owner_id':self.merchand_id.id
                })
            picking_id.action_confirm()
            for move_line in picking_id.move_line_ids_without_package:
                move_line.qty_done = move_line.product_uom_qty
                move_line.lot_id=lot_id.id
            
            lines = picking_id.mapped("move_line_ids").filtered(
                lambda x: (
                    not x.lot_id
                    and not x.lot_name
                    and x.product_id.tracking != "none"
                    
                )
            )
            lines.set_lot_auto(lot_id)
            if picking_id.state == 'draft':
                picking_id.action_confirm()
            line.return_stock_picking_id=picking_id.id
            
        self.status_return='return_rec'

    def action_raise_dispute(self):
        team_id=self.env['helpdesk.team'].sudo().search([('name','=','WO Schedule Date Dispute')],limit=1)

        ticket_data={
        'partner_id':self.merchand_id.id,
        'team_id':team_id.id,
        'name':"WO Dispute -"+self.name,
        'wo_dispute_id':self.id,
        'description':self.dispute_description
        }
        ticket_id = self.env['helpdesk.ticket'].sudo().create(ticket_data)
        for user in team_id.visibility_member_ids:
            ticket_id.sudo().activity_schedule('ag_the_hub.mail_activity_wo_dispute', user_id=user.id)

        body = _("<strong>Your request Dispute - %s has been received and is being reviewed by our WO Dispute Teams team. The reference of your ticket is %s. </div>",ticket_id.name,ticket_id.id)
            

        self.message_post(body=body)
        self.dispute_raised=True




    @api.onchange('shipping_to','packing_categ','packing_type_id')
    def _onchange_partner(self):
        self.package_lines=False
        if self.shipping_to == 'diff_addres':
            for line in self.wo_line_ids:
                line.packing_categ=False
                line.packing_type_id=False
        else:
            for line in self.wo_line_ids:
                line.packing_categ=self.packing_categ
                line.packing_type_id=self.packing_type_id




    def _compute_show_receive_btn_done(self):
        current_user = self.env.user
        
        user_ids = self.env.company.receiver_user_ids
        for rec in self:
            rec.show_receive_btn_done = False
            if current_user.id in user_ids.ids:
                domain = [
                    ('res_model', '=', 'thehub.workorder'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_return_process_pending_wo').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_receive_btn_done = True
    

    


    def _compute_picking_count(self):
        for rec in self:
            picking_ids = self.env['stock.picking'].search([('wo_id','=',self.id)])
            rec.picking_count=len(picking_ids.ids)



    def action_open_picking(self):
        picking_ids = self.env['stock.picking'].search([('wo_id','=',self.id)])
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

    

    def _compute_show_picking_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.picker_user_ids
        for rec in self:
            if rec.wo_type =='delivery':
                rec.show_picking_done_btn = False
                if current_user.id in user_ids.ids and not rec.wo_picking_done:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_pending_wo').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        rec.show_picking_done_btn = True
            else:
                rec.show_picking_done_btn = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_return_wo').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        rec.show_picking_done_btn = True

    def action_picking_done(self):
        for line in self.wo_line_ids:
            if line.scan_package_number and not line.is_validated:
                msg='Please Validate package with number  '+ line.scan_package_number
                raise ValidationError(msg)

        if self.wo_line_ids:
            SaleOrder=self.env['sale.order'].sudo()
            sale_order_line=self.env['sale.order.line'].sudo()
            sale_order = SaleOrder.create({
                    'partner_id': self.merchand_id.id,
                    'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                    'wo_id':self.id,
                    'note':'Oubount Rule -- '+self.name
                    #'team_id': team.id if team else False,
                })

            for line in self.wo_line_ids:
                if line.wro_shipping_type_new == 'parcel':
                    if line.send_as_new == 'non_consolidated':
                        sale_order_line_id=sale_order_line.create({
                            'product_id':self.company_id.outgoing_box_cost_noncons_product.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_noncons_product.id,
                            'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_noncons_product.name,
                            'product_uom_qty':line.product_qty,
                            'price_unit':self.company_id.outgoing_box_cost_noncons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_noncons,
                            'order_id':sale_order.id
                                    
                            })
                    else:
                        sale_order_line_id=sale_order_line.create({
                            'product_id':self.company_id.outgoing_box_cost_cons_product.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_cons_product.id,
                            'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_cons_product.name,
                            'product_uom_qty':1,
                            'price_unit':self.company_id.outgoing_box_cost_cons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_box_cost_cons,
                            'order_id':sale_order.id
                                    
                            })
                    # sale_order_line_id.product_id_change()
                    # price_unit=sale_order_line_id.price_unit
                    # sale_order_line_id.write({'name':self.name+'-'+line.product_id.name,'price_unit':price_unit})

                else:
                    if line.send_as_new == 'non_consolidated':
                        sale_order_line_id=sale_order_line.create({
                            'product_id':self.company_id.outgoing_pallet_cost_noncons_product.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_noncons_product.id,
                            'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_noncons_product.name,
                            'product_uom_qty':line.product_qty,
                            'price_unit':self.company_id.outgoing_pallet_cost_noncons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_noncons,
                            'order_id':sale_order.id
                                    
                            })
                    else:
                        sale_order_line_id=sale_order_line.create({
                            'product_id':self.company_id.outgoing_pallet_cost_cons_product.id if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_cons_product.id,
                            'name':self.name+'-'+line.product_id.name if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_cons_product.name,
                            'product_uom_qty':1,
                            'price_unit':self.company_id.outgoing_pallet_cost_cons if not self.merchand_id.billing_type.special_price_enable else self.merchand_id.billing_type.outgoing_pallet_cost_cons,
                            'order_id':sale_order.id
                                    
                            })
                    # sale_order_line_id.product_id_change()
                    # price_unit=sale_order_line_id.price_unit
                    # sale_order_line_id.write({'name':self.name+'-'+line.product_id.name,'price_unit':price_unit})

                # sale_order_line_id.product_id_change()
                # sale_order_line_id.write({'name':self.name+'-'+line.product_id.name})
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


        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_pending_wo').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Picking Done")
        packer_user_ids = self.env.company.packer_user_ids
        for user_id in packer_user_ids:
            domain = [
                ('res_model', '=', 'thehub.workorder'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_packing').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.activity_schedule('ag_the_hub.mail_activity_process_packing', user_id=user_id.id)
        self.wo_picking_done = True
        self.status = "Awaiting"
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', self.company_id.id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        picking_type_id=picking_type[:1]
        if picking_type_id.default_location_dest_id:
            location_dest_id = picking_type_id.default_location_dest_id.id
        elif self.merchand_id:
            location_dest_id = self.merchand_id.property_stock_customer.id
        else:
            location_dest_id, supplierloc = self.env['stock.warehouse'].sudo()._get_partner_locations()

        
        for line in self.wo_line_ids:
            lot_id = line.package_id
            line_ids = []
            line_ids.append((0,0,{
                    'product_id': line.product_id.id,
                    'name': line.product_id.display_name,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_dest_id': location_dest_id,
                    'location_id': line.source_location.id,
                    'lot_ids':[(6,0,lot_id.ids)]
                }))
            picking_id = self.env['stock.picking'].sudo().create({
                    'partner_id':self.merchand_id.id,
                    'picking_type_id': picking_type_id.id,
                    'location_dest_id': location_dest_id,
                    'location_id': line.source_location.id,
                    'move_ids_without_package': line_ids,
                    'origin': line.package_id.name,
                    'wo_id':self.id,
                    'owner_id':self.merchand_id.id
                })
            # lines = picking_id.mapped("move_line_ids").filtered(
            #     lambda x: (
            #         not x.lot_id
            #         and not x.lot_name
            #         and x.product_id.tracking != "none"
            #         and x.product_id.auto_create_lot
            #     )
            # )
            # lines.set_lot_auto(lot_id)
            line.stock_picking_id=picking_id.id
            # for picking_line in picking_id.move_line_ids:
            #     picking_line.write({'lot_id':lot_id.id})
            if picking_id.state == 'draft':
                picking_id.action_confirm()
        
            # picking_id.with_context(skip_immediate=True).button_validate()

    def _compute_show_packing_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.packer_user_ids
        for rec in self:
            rec.show_packing_done_btn = False
            if rec.wo_type == 'delivery':
                if current_user.id in user_ids.ids and not rec.wo_packing_done:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_packing').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        rec.show_packing_done_btn = True
            else:
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_return_process_pending_wo').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        rec.show_packing_done_btn = True




    def action_packing_done(self):
        # if self.payment_type == 'My own 3PL Arrangement':
        #     # for line in self.wo_line_ids:
        #     #     if not line.is_validated or not line.schedule_pickup:
        #     #         raise ValidationError('Please Validate Or Schedule time for pickup')
        #     if not self.schedule_pickup:
        #         raise ValidationError('Please Schedule time for pickup')

        #     for line in self.wo_line_ids:
        #         if not line.is_validated:
        #             raise ValidationError('Please Validate All lines First')
        #     self.status='Pickup Time Assigned'
        # else:
        if not self.package_lines:
            raise ValidationError('Please Fill Packing Categ Or Packing Type or weight')
        for line in self.package_lines:
            if not line.packing_categ or not line.packing_type_id:
                raise ValidationError('Please Fill Packing Categ Or Packing Type or weight')
        if self.wo_line_ids:
            SaleOrder=self.env['sale.order'].sudo()
            sale_order_line=self.env['sale.order.line'].sudo()
            


            sale_order = SaleOrder.create({
                    'partner_id': self.merchand_id.id,
                    'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                    'wo_id':self.id
                    #'team_id': team.id if team else False,
                })

            for line in self.package_lines:
                packing_template=False
                if not line.non_billable:
                    if self.merchand_id.billing_type:
                        for rec in self.merchand_id.billing_type.packing_template_ids:
                            if rec.packing_type_id==line.packing_type_id:
                                packing_template=rec
                                break
                    sale_order_line_id=sale_order_line.create({
                        'product_id':line.packing_type_id.product_id.id if not packing_template else packing_template.product_id.id,
                        'name':self.name+'-'+line.packing_type_id.product_id.name,
                        'product_uom_qty':1,
                        'price_unit':line.packing_type_id.price if not packing_template else packing_template.price,
                        'order_id':sale_order.id
                                
                        })
            if sale_order.order_line:
                #sale_order_line_id.product_id_change()
                #sale_order_line_id.write({'name':self.name+'-'+line.product_id.name,'price_unit':line.packing_type_id.price})
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
            else:
                sale_order.sudo().unlink()





        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_packing').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Packing Done")
        dispatch_user_ids = self.env.company.dispatch_user_ids
        for user_id in dispatch_user_ids:
            domain = [
                ('res_model', '=', 'thehub.workorder'),
                ('res_id', 'in', self.ids),
                ('user_id', '=', user_id.id),
                ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_dispatch').id),
            ]
            activities = self.env['mail.activity'].sudo().search(domain)
            if not activities:
                self.activity_schedule('ag_the_hub.mail_activity_process_dispatch', user_id=user_id.id)
        self.wo_packing_done = True

    def _compute_show_dispatch_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.dispatch_user_ids
        for rec in self:
            rec.show_dispatch_done_btn = False
            rec.show_dispatch_not_done_btn = False
            if current_user.id in user_ids.ids and (not rec.wo_dispatch_done or not rec.wo_return_done):
                domain = [
                    ('res_model', '=', 'thehub.workorder'),
                    ('res_id', 'in', rec.ids),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_dispatch').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if activities:
                    rec.show_dispatch_done_btn = True
                    rec.show_dispatch_not_done_btn = True

    def action_dispatch_done(self):

        for line in self.package_lines:
            if line.name != line.scan_package_number:
                warning_msg='The Shipping ID is not correct. Please check and rescan'
                raise ValidationError(warning_msg)
        if self.payment_type == 'My own 3PL Arrangement':
            team_id=self.env['helpdesk.team'].sudo().search([('name','=','WO Dispatch')],limit=1)
            description="<div>3PL Company Name  :- %s</div><div>3PL Company Email :- %s</div><div>3PL Company mobile :- %s</div>"%(self.three_plcompany.name,self.three_plcompany.email,self.three_plcompany.phone)

            ticket_data={
            'partner_id':self.merchand_id.id,
            'team_id':team_id.id,
            'name':"3PL Dispatch - WO -"+self.name,
            'wo_id':self.id,
            'description':description
            }
            ticket_id = self.env['helpdesk.ticket'].sudo().create(ticket_data)
            #ticket_id.wo_id = self.id
            for user in team_id.visibility_member_ids:
                ticket_id.sudo().activity_schedule('ag_the_hub.mail_activity_wo_dispatch', user_id=user.id)

            body = _("<strong>Your request Dispatch - %s has been received and is being reviewed by our WO Dispatch team. The reference of your ticket is %s. </div>",ticket_id.name,ticket_id.id)
                

            self.message_post(body=body)
        self.wo_dispatch_done = True
        self.wo_dispatch_date = fields.Date.today()
        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_dispatch').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Workorder Dispatched")

        for line in self.wo_line_ids:
            if line.stock_picking_id:
                
                if line.stock_picking_id.state == 'draft':
                    line.stock_picking_id.action_confirm()
                for move_line in line.stock_picking_id.move_line_ids_without_package:
                    move_line.qty_done = move_line.product_uom_qty
                        
                line.stock_picking_id.with_context(skip_immediate=True,skip_backorder=True, skip_sms=True).button_validate()
        
        
        self.status = "Dispatched"
        

    def action_delivery_return(self):
        return_id=self.copy({'wo_type': 'return','status_return':'return_gen'})
        # picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', self.company_id.id)])
        # if not picking_type:
        #     picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        # picking_type_id=picking_type[:1]
        # if picking_type_id.default_location_dest_id:
        #     location_dest_id = picking_type_id.default_location_dest_id.id
        
        workorder_line_rec = []
        
        for item in self.wo_line_ids:
            # wo_line_dic = {}
            # rec = int(item.split('_')[2])
            # quant_id = request.env['stock.quant'].sudo().browse(rec)
            # if kw.get('quantity_{}'.format(rec)):
            # #     wo_line_dic.update({'product_qty': kw.pop('quantity_{}'.format(rec))})
            # lot_id = self.env['stock.production.lot'].sudo().search([('name','=',item.stock_picking_id.origin)])
            # if not lot_id:
            #     lot_id = self.env['stock.production.lot'].sudo().create({
            #                 'name':item.stock_picking_id.origin,
            #                 'product_id':item.product_id.id,
            #                 'company_id':self.company_id.id,
            #                 'product_qty':item.product_qty
            #                 })
            # line_ids = []
            # line_ids.append((0,0,{
            #         'product_id': item.product_id.id,
            #         'name': item.product_id.display_name,
            #         'product_uom_qty': item.product_qty,
            #         'product_uom': item.product_id.uom_id.id,
            #         'location_id': item.stock_picking_id.location_dest_id.id,
            #         'location_dest_id': item.stock_picking_id.location_id.id,
            #         'lot_ids':[(6,0,lot_id.ids)]
            #     }))
            # picking_id = self.env['stock.picking'].sudo().create({
            #         'partner_id':self.merchand_id.id,
            #         'picking_type_id': picking_type_id.id,
            #         'location_id': item.stock_picking_id.location_dest_id.id,
            #         'location_dest_id': item.stock_picking_id.location_id.id,
            #         'move_ids_without_package': line_ids,
            #         'origin': item.stock_picking_id.origin,
            #         'wo_id':return_id.id,
            #         'owner_id':self.merchand_id.id
            #     })
            # picking_id.action_confirm()
            # for move_line in picking_id.move_line_ids_without_package:
            #     move_line.qty_done = move_line.product_uom_qty
            #     move_line.lot_id=lot_id.id
            # # picking_id.action_assign()
            # # print("eeeeeeeeeeeeeeeeeeeeee",picking_id.move_line_ids_without_package.qty_done)
            
            # lines = picking_id.mapped("move_line_ids").filtered(
            #     lambda x: (
            #         not x.lot_id
            #         and not x.lot_name
            #         and x.product_id.tracking != "none"
                    
            #     )
            # )
            # lines.set_lot_auto(lot_id)
            # # for picking_line in picking_id.move_line_ids:
            # #     picking_line.write({'lot_id':lot_id.id})
            # if picking_id.state == 'draft':
            #     picking_id.action_confirm()
            wo_line_dic={
                'package_id':item.package_id.id,
                'product_id': item.product_id.id,
                'send_qty':item.send_qty,
                'product_qty':item.product_qty,
                'delivery_address':item.delivery_address,
                'stock_picking_id':item.stock_picking_id.id,
               
                }
            if wo_line_dic:
                workorder_line_rec.append((0,0,wo_line_dic)) 
            


        return_id.write({'wo_line_ids':workorder_line_rec})   
        self.return_wo_id=return_id.id
        self.status='Returned'


    def action_delivery_done(self):
        #line.stock_picking_id.with_context(skip_immediate=True).button_validate()
        
        
        self.status = 'Delivered'
        SaleOrder=self.env['sale.order'].sudo()
        sale_order_line=self.env['sale.order.line'].sudo()
            
        sale_order = SaleOrder.create({
                'partner_id': self.merchand_id.id,
                'company_id': self.merchand_id.company_id.id if self.merchand_id.company_id else self.env.user.company_id.id,
                'wo_id':self.id
                #'team_id': team.id if team else False,
            })

        sale_order_line_id=sale_order_line.create({
            'product_id':self.env.user.company_id.thl_shipping_product_id.id,
            'name':self.name+'-'+self.env.user.company_id.thl_shipping_product_id.name,
            'product_uom_qty':1,
            'price_unit':self.env.user.company_id.thl_shipping_cost,
            'order_id':sale_order.id
                    
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



    def action_dispatch_not_done(self):
        domain = [
            ('res_model', '=', 'thehub.workorder'),
            ('res_id', 'in', self.ids),
            ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_dispatch').id),
        ]
        activities = self.env['mail.activity'].sudo().search(domain)
        if activities:
            activities.sudo().action_feedback(feedback="Workorder Not Dispatched")
        self.wo_return_done = True
        self.status = "Returned"



    @api.model
    def create(self, vals):
        res = super(Workorder, self).create(vals)
        if not res.name:
            if res.wo_type =='delivery':
                sequence_id = self.env.ref('ag_the_hub.sequence_thehub_workorder')
                seq = sequence_id.next_by_id()
                res.name = seq
            else:
                sequence_id = self.env.ref('ag_the_hub.sequence_thehub_workorder_return')
                seq = sequence_id.next_by_id()
                res.name = seq
        if res.wo_type=='delivery':
            user_ids = self.env.company.picker_user_ids
            for user_id in user_ids:
                domain = [
                    ('res_model', '=', 'thehub.workorder'),
                    ('res_id', 'in', res.ids),
                    ('user_id', '=', user_id.id),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_pending_wo').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    res.activity_schedule('ag_the_hub.mail_activity_process_pending_wo', user_id=user_id.id)
        else:
            user_ids = self.env.company.receiver_user_ids
            for user_id in user_ids:
                domain = [
                    ('res_model', '=', 'thehub.workorder'),
                    ('res_id', 'in', res.ids),
                    ('user_id', '=', user_id.id),
                    ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_return_process_pending_wo').id),
                ]
                activities = self.env['mail.activity'].sudo().search(domain)
                if not activities:
                    res.activity_schedule('ag_the_hub.mail_activity_return_process_pending_wo', user_id=user_id.id)
        return res


    def action_delete_selected_line(self):
        for line in self.wo_line_ids:
            if line.select:
                line.unlink()

    def action_select_all_line(self):
        for line in self.wo_line_ids:
            line.select=True

    def action_mark_as_validate(self):
        for line in self.wo_line_ids:
            line.select=False
            line.validate()

    def get_pickup_location(self):
        source_location_ids = self.wo_line_ids.mapped('source_location')
        if source_location_ids:
            return source_location_ids[0].warehouse_id.name
        return False

    def get_lines_data(self):
        data_lst = []
        product_ids = []
        for rec in self.wo_line_ids:
            vals = {}
            if rec.product_id.id not in product_ids:
                vals['product_name'] = rec.product_id.name
                vals['internal_reference'] = rec.product_id.default_code
                packing_categ = self.package_lines.filtered(lambda x: rec.id in x.product_lines.ids).mapped('packing_categ')
                vals['packing_categ'] = packing_categ[0] if packing_categ else False
                product_qty = sum(self.wo_line_ids.filtered(lambda x: x.product_id.id == rec.product_id.id).mapped('product_qty'))
                vals['product_qty'] = product_qty
                data_lst.append(vals)
                product_ids.append(rec.product_id.id)
        return data_lst

    def get_conatct_number_thl(self):
        source_location_ids = self.wo_line_ids.mapped('source_location')
        if source_location_ids:
            return source_location_ids[0].warehouse_id.partner_id.phone
        return False

    def action_print_wo_manifest(self):
        return self.env.ref('ag_the_hub.action_print_wo_manifest_report').report_action(self)

class WorkorderLines(models.Model):
    _name = "thehub.workorder.lines"
    _description = "Workorder Lines"

    def action_update_package_number(self):
        if not self:
            raise UserError(_("Please select Line first"))


        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'name': _('Update Location'),
            'res_model': 'update.package.number',
             'target': 'new',
             'context':{'default_line_ids':[(6,0,self.ids)]},
             
            
            
        }
        return action 

    def action_validate_lines(self):
        for line in self:
            line.validate()




    select = fields.Boolean("Select")
    workorder_id = fields.Many2one("thehub.workorder", string="Workorder")
    product_id = fields.Many2one("product.product", string="Product")
    product_qty = fields.Float("Quantity")
    send_as = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Send As", default="consolidated")
    wro_shipping_type = fields.Selection([('parcel', 'Parcel (standard shipping)'),
                                      ('pallet', 'Palletized container or LTL (less-than-truckload)'),
                                      ('container', 'Floor loaded container')], string="Shipping Type")


    send_as_new = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Send As", default="consolidated")
    wro_shipping_type_new = fields.Selection([('parcel', 'Parcel (standard shipping)'),
                                      ('pallet', 'Palletized container or LTL (less-than-truckload)'),
                                      ('container', 'Floor loaded container')], string="Shipping Type")
    
    package_id = fields.Many2one('stock.production.lot',string="Package")
    send_qty = fields.Float('Send QTY')
    source_location = fields.Many2one('stock.location',string="Source Location")
    delivery_address = fields.Text("Delivery Address")
    location_label = fields.Char('Location Label',copy=False)
    scan_package_number = fields.Char("Scanned package Number",copy=False,)
    scanned_qty = fields.Float("Scanned Quantity",copy=False)
    is_validated = fields.Boolean()
    payment_type = fields.Selection(related="workorder_id.payment_type",store=True, string="Payment Type")
    
    show_picking_done_btn = fields.Boolean(string="Show Picking Done Button" ,compute='_compute_show_picking_done_btn')
    show_packing_done_btn = fields.Boolean(string="Show Packing Done Button" ,compute='_compute_show_packing_done_btn')
    custom_show_packing_done_btn = fields.Boolean(string="Show Packing Done Button" ,compute='_compute_show_packing_done_users')
    
    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")

    packing_type_id = fields.Many2one('thehub.packing.type',domain="[('packing_categ', '=', packing_categ)]")
    stock_picking_id = fields.Many2one('stock.picking',string="Picking")
    scanned_shipping_label = fields.Char("Scan Shipping label",copy=False)
    return_stock_picking_id = fields.Many2one('stock.picking',string="Return Picking")
    
    # carton_packing  = fields.Selection([('Small', 'Small'),
    #                                 ('Medium', 'Medium'),
    #                                 ('Large', 'Large'),
    #                                 ('Custom', 'Custom')], string="Carton Packing Box")
    # flyer_packing  = fields.Selection([('Small', 'Small'),
    #                                 ('Medium', 'Medium'),
    #                                 ('Large', 'Large'),
    #                                 ('XLarge', 'XLarge')], string="Flyer Packing Box")
    # pallet_packing  = fields.Selection([('Standard One Size', 'Standard One Size')
    #                                 ], string="Pallet Packing Box")
    shipping_to = fields.Selection(related="workorder_id.shipping_to",store=True, string="Shipping to")
    validate_shipping_label = fields.Boolean()
    show_receive_btn_done = fields.Boolean(string="Show Packing Done Button" ,compute='_compute_show_receive_btn_done')
    weight = fields.Float("Weight In KG")
    return_reason = fields.Selection([('defective','Defective Product'),
                                    ('wrong_item','Wrong Item Shipped'),
                                    ('damage','Product Damaged in Transit'),
                                    ('not_needed','No Longer Needed'),
                                    ('size_issue','Size/Measurement Issue'),
                                    ('customer_preference','Customer Preference'),
                                    ('other','Other')],string="Return Reason")

    manual_line = fields.Boolean('Manual Line')
    package_ids = fields.Many2many('stock.production.lot',string="Package")
    comment = fields.Char("")


    def action_cascade_wo_line(self):
        for rec in self:
            rec.scan_package_number = rec.package_id.name
            rec.location_label = rec.source_location.location_scan_name
            rec.scanned_qty = rec.product_qty


    def _compute_show_receive_btn_done(self):
        current_user = self.env.user
        
        user_ids = self.env.company.receiver_user_ids
        for record in self:
            for rec in record.workorder_id:
                record.show_receive_btn_done = False
                if current_user.id in user_ids.ids:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_return_process_pending_wo').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_receive_btn_done = True



    def action_validate_shipping_label(self):

        if self.stock_picking_id.name != self.scanned_shipping_label:
            raise ValidationError(_('Scanned shipping label not matched please check'))
        self.validate_shipping_label=True




    def _compute_show_packing_done_users(self):
        current_user = self.env.user
        user_ids = self.env.company.packer_user_ids
        for record in self:
            for rec in record.workorder_id:
                record.custom_show_packing_done_btn = False
                if current_user.id in user_ids.ids:
                    
                    record.custom_show_packing_done_btn = True



    

    def _compute_show_packing_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.packer_user_ids
        for record in self:
            for rec in record.workorder_id:
                record.show_packing_done_btn = False

                if current_user.id in user_ids.ids and not rec.wo_packing_done:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_packing').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_packing_done_btn = True

    


    def validate(self):
        if not self.source_location or not self.location_label or not self.scan_package_number:
            raise ValidationError(_('Please check location and location_label and package_number'))
        elif self.scan_package_number != self.package_id.name and self.product_id.default_code != self.scan_package_number:
            raise ValidationError(_('Package Number or Product Internal Ref not matched please check'))
        elif self.source_location.location_scan_name != self.location_label:
            raise ValidationError(_('location not matched please check'))
        elif self.product_qty != self.scanned_qty:
            raise ValidationError(_('Scanned Quantity not matched please check'))
            
        self.is_validated=True

        
    

    def _compute_show_picking_done_btn(self):
        current_user = self.env.user
        user_ids = self.env.company.picker_user_ids
        for record in self:
            for rec in record.workorder_id:
                record.show_picking_done_btn = False
                if current_user.id in user_ids.ids and not rec.wo_picking_done:
                    domain = [
                        ('res_model', '=', 'thehub.workorder'),
                        ('res_id', 'in', rec.ids),
                        ('activity_type_id', '=', self.env.ref('ag_the_hub.mail_activity_process_pending_wo').id),
                    ]
                    activities = self.env['mail.activity'].sudo().search(domain)
                    if activities:
                        record.show_picking_done_btn = True



    def print_shipping_label(self):
        if not self.packing_categ or not self.packing_type_id:
            raise ValidationError('Please Fill Packing Categ Or Packing Type')


        target_url =  self.sudo().env['ir.config_parameter'].get_param('web.base.url') +"/print/shipping/label/"+str(self.id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'state': self.id,
            'url': target_url
        }



    def validate_return(self):
        if not self.location_label or not self.scan_package_number:
            raise ValidationError(_('Please check location and location_label and package_number'))
        elif self.scan_package_number != self.package_id.name:
            raise ValidationError(_('Package Number not matched please check'))
        elif self.source_location.location_scan_name != self.location_label:
            raise ValidationError(_('location not matched please check'))
        elif self.product_qty != self.scanned_qty:
            raise ValidationError(_('Scanned Quantity not matched please check'))
        # elif self.stock_picking_id.name != self.scanned_shipping_label:
        #     raise ValidationError(_('Scanned shipping label not matched please check'))
                
        self.is_validated=True



class WorkorderLinesPackage(models.Model):
    _name = "thehub.workorder.lines.package"
    _description = "Workorder Lines Package"


    select = fields.Boolean('Select')
    name = fields.Char(string='Package Number',readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('thehub.workorder.lines.package'))
    address = fields.Text('Address')
    product_lines = fields.Many2many('thehub.workorder.lines')
    wo_id =fields.Many2one('thehub.workorder')
    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")
    packing_type_id = fields.Many2one('thehub.packing.type',domain="[('packing_categ', '=', packing_categ),('packing_type','=','wo')]")
    non_billable = fields.Boolean('Not chargable')
    weight = fields.Float('Weight')
    scan_package_number = fields.Char("Scanned package Number",copy=False,)
    
    is_validated = fields.Boolean()
    # show_packing_done_btn = fields.Boolean(related="wo_id.show_packing_done_btn")


    def validate_packing(self):
        if not self.scan_package_number:
            raise ValidationError(_('Please check location_label'))
        elif self.name != self.scan_package_number:
            raise ValidationError(_('Package not matched please check'))
        self.is_validated=True


    def print_shipping_label(self):
        if not self.packing_categ or not self.packing_type_id:
            raise ValidationError('Please Fill Packing Categ Or Packing Type')


        target_url =  self.sudo().env['ir.config_parameter'].get_param('web.base.url') +"/print/shipping/label/package/"+str(self.id)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'state': self.id,
            'url': target_url
        }

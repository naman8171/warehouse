
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime

class WoLineImport(models.TransientModel):
    _name = "wo.line.import"
    _description = "Wo Line Import"


    product_ids = fields.Many2many('product.product', string="Products", compute="_compute_product_ids")
    product_id = fields.Many2one('product.product',string="Product")
    available_qty = fields.Integer("Available Quantity",readonly=True)
    send_qty = fields.Integer(string="Send QTY")
    package_id = fields.Many2many('stock.quant',string="Package")
    wo_id = fields.Many2one('thehub.workorder')
    wro_shipping_type = fields.Selection([('parcel', 'Parcel (standard shipping)'),
                                      ('pallet', 'Palletized container or LTL (less-than-truckload)'),
                                      ('container', 'Floor loaded container')], string="Shipping Type")

    send_as = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Send As", default="consolidated")
    is_manual = fields.Boolean('Is Manual')

    delivery_address = fields.Text('Delivery Address')
    weight = fields.Float('Weight')



    # @api.onchange('wro_shipping_type','send_as')
    # def _onchange_wro_shipping(self):
    #     self.product_id=False
    #     self.package_id=False
        # self._onchange_product()


    @api.onchange('package_id')
    def _onchange_package_id(self):
        count=0
        product_qty = self.send_qty
        for package in self.package_id:
            if count!=0:
                self.package_id=False
                break
            stock_product = package
            quantity=stock_product.quantity - stock_product.reserved_quantity
            if quantity>0:
                product_qty=product_qty-quantity
                if product_qty<=0:
                    count=1

    @api.depends('send_as')
    def _compute_product_ids(self):
        for rec in self:
            stock_products = self.env['stock.quant'].sudo().search([
                '|', 
                ('owner_id', '=', rec.wo_id.merchand_id.id), 
                ('owner_id.child_ids', 'in', rec.wo_id.merchand_id.ids),
                ('consolidated_type', '=', rec.send_as)
            ])
            
            rec.product_ids = [(6, 0, stock_products.mapped('product_id').ids)]


    @api.onchange('product_id','wro_shipping_type','send_as')
    def _onchange_product(self):
        # if not self.product_id:
        #     product_list=[]
        #     stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids', 'in', self.wo_id.merchand_id.ids),('consolidated_type','=',self.send_as)])
        #     inventory_ids_list =[]
        #     for quant in stock_product:
        #         quantity=quant.quantity - quant.reserved_quantity
        #         # if quantity>0:
        #         product_list.append(quant.product_id.id)
        #     #product_list_ids = self.env['product.product'].sudo().search([('id','in',product_list)])
        #     domain = [('id', 'in', product_list)]
        #     return {'domain': {'product_id': domain}}

        # else:
        if self.product_id:
            stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids', 'in', self.wo_id.merchand_id.ids), ('product_id','=',self.product_id.id),('consolidated_type','=',self.send_as)])
            total_qty =0
            for quant in stock_product:
                quantity=quant.quantity - quant.reserved_quantity
                if quantity>0:
                    total_qty+=quantity
            self.available_qty=total_qty
            stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids', 'in', self.wo_id.merchand_id.ids), ('product_id','=',self.product_id.id),('consolidated_type','=',self.send_as)])
            inventory_ids_list =[]
            for quant in stock_product:
                quantity=quant.quantity - quant.reserved_quantity
                if quantity>0:
                    inventory_ids_list.append(quant.id)
                    #print("dddddddddddddddddddddddddddd",quant.consolidated_type,quantity)
            #product_list_ids = self.env['product.product'].sudo().search([('id','in',product_list)])
            domain = [('id', 'in', inventory_ids_list)]
            return {'domain': {'package_id': domain}}





    @api.onchange('send_qty')
    def _onchange_send_qty(self):
        if self.send_qty>self.available_qty:
            self.send_qty=0


    def import_line(self):
        if self.wo_id and self.wo_id.merchand_id:
            wo_line_dic = {}
            if self.wo_id.merchand_id.wo_stock_type !='manually':
                if self.wo_id.merchand_id.wo_stock_type == 'lifo':
                    stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids', 'in', self.wo_id.merchand_id.ids), ('location_id.usage','=','internal'),('product_id','=',self.product_id.id),('consolidated_type','=',self.send_as)],order='create_date desc')
                elif self.wo_id.merchand_id.wo_stock_type == 'fifi':
                    stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids', 'in', self.wo_id.merchand_id.ids), ('location_id.usage','=','internal'),('product_id','=',self.product_id.id),('consolidated_type','=',self.send_as)],order='create_date asc')
                
                total_qty =0
                quant_ids =[]
                total_qty=0
                location_ids=[]
                for quant in stock_product:
                    quantity=quant.quantity - quant.reserved_quantity
                    if quantity>0 and self.send_qty>total_qty:
                        total_qty+=quantity
                        quant_ids.append(quant.id)
                        location_ids.append(quant.location_id.id)
                required_quantity=self.send_qty
                for quant in quant_ids:
                    stock_product = self.env['stock.quant'].sudo().browse(quant)
                    required_quantity=self.send_qty
                    required_quantity=required_quantity-(stock_product.quantity - stock_product.reserved_quantity)
                    qty=0
                    if required_quantity>0:
                        qty=stock_product.quantity - stock_product.reserved_quantity
                    else:
                        qty=self.send_qty


                    self.wo_id.write({'wo_line_ids':[(0,0,{
                    'package_id':stock_product.lot_id.id,
                    'product_qty':qty,
                    'product_id': self.product_id.id,
                    'send_qty':self.available_qty,
                    'send_as':self.send_as,
                    'wro_shipping_type':self.wro_shipping_type,
                    'send_as_new':self.send_as,
                    'wro_shipping_type_new':'parcel' if self.wo_id.shipping_type == 'Parcel' else False,
                    'manual_line':False,
                    'source_location':stock_product.location_id.id,
                    'delivery_address':self.delivery_address,
                    'weight':self.weight
                    })]})
                

                # self.wo_id.write({'wo_line_ids':[(0,0,{
                #     'package_ids':[(6,0,quant_ids)],
                #     'product_qty':self.send_qty,
                #     'product_id': self.product_id.id,
                #     'send_qty':self.available_qty,
                #     'send_as':self.send_as,
                #     'wro_shipping_type':self.wro_shipping_type,
                #     'send_as_new':self.send_as,
                #     'wro_shipping_type_new':'parcel' if self.wo_id.shipping_type == 'Parcel' else False,
                #     'manual_line':True,
                #     'source_location_ids':[(6,0,location_ids)],
                #     'delivery_address':self.delivery_address,
                #     'weight':self.weight
                #     })]})
            else:
                quant_ids =[]
                location_ids=[]
                
                
                for quant in self.package_id:
                    quant_ids.append(quant.lot_id.id)
                    location_ids.append(quant.location_id.id)
                    required_quantity=self.send_qty
                    required_quantity=required_quantity-(quant.quantity - quant.reserved_quantity)
                    qty=0
                    if required_quantity>0:
                        qty=quant.quantity - quant.reserved_quantity
                    else:
                        qty=self.send_qty


                    self.wo_id.write({'wo_line_ids':[(0,0,{
                        'package_id':quant.lot_id.id,
                        'product_qty':qty,
                        'product_id': self.product_id.id,
                        'send_qty':self.available_qty,
                        'send_as':self.send_as,
                        'wro_shipping_type':self.wro_shipping_type,
                        'send_as_new':self.send_as,
                        'wro_shipping_type_new':'parcel' if self.wo_id.shipping_type == 'Parcel' else False,
                        'manual_line':False,
                        'source_location':quant.location_id.id,
                        'delivery_address':self.delivery_address,
                        'weight':self.weight
                        
                        # 'delivery_address':kw.pop('delivery_address_{}'.format(rec))
                        })]})

            # self.wo_id.write({
            #     ''
            #     })

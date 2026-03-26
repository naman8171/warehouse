# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class BillingType(models.Model):
    _name = "billing.type"


    name = fields.Char('Name')
    days = fields.Integer(string="Days")
    packing_template_ids = fields.One2many('packaging.template','billing_type')
    box_template_ids = fields.One2many('box.template','billing_type')
    storage_template_ids = fields.One2many('storage.template','billing_type')
    
    special_price_enable = fields.Boolean('Special Price Enable')
    storage_type = fields.Selection([('Shared','Shared'),('Dedicated','Dedicated')],string="Storage Dynamics",default="Shared")
    



    incoming_pallet_cost_cons = fields.Float("Incoming Pallet Cost Consoladited")
    incoming_pallet_cost_cons_product = fields.Many2one('product.product')

    incoming_pallet_cost_noncons = fields.Float("Incoming Pallet Cost Non-Consoladited")
    incoming_pallet_cost_noncons_product = fields.Many2one('product.product')



    incoming_box_cost_cons = fields.Float("Incoming Box Cost Consoladited")
    incoming_box_cost_cons_product = fields.Many2one('product.product')


    incoming_box_cost_noncons = fields.Float("Incoming Box Cost Non-Consoladited")
    incoming_box_cost_noncons_product = fields.Many2one('product.product')


    outgoing_pallet_cost_cons = fields.Float("Outgoing Pallet Cost Consoladited")
    outgoing_pallet_cost_cons_product = fields.Many2one('product.product')


    outgoing_pallet_cost_noncons = fields.Float("Outgoing Pallet Cost Non-Consoladited")
    outgoing_pallet_cost_noncons_product = fields.Many2one('product.product')



    outgoing_box_cost_cons = fields.Float("Outgoing Box Cost Consoladited")
    outgoing_box_cost_cons_product = fields.Many2one('product.product')


    outgoing_box_cost_noncons = fields.Float("Outgoing Box Cost Non-Consoladited")
    outgoing_box_cost_noncons_product = fields.Many2one('product.product')

    
    



    
class PackagingTemplate(models.Model):
    _name = "packaging.template"


    packing_type_id = fields.Many2one('thehub.packing.type',string="Packing Type")
    price = fields.Float(related="product_id.list_price",string="Price",store=True)
    billing_type = fields.Many2one("billing.type",string="Billing Type")
    product_id = fields.Many2one('product.product',string="Product")
    packing_type = fields.Selection(related="packing_type_id.packing_type", string="Packing Related to",readonly=True)
    


    @api.onchange('packing_type_id','product_id')
    def onchange_packing_type_id(self):
        if self.packing_type_id:
            self.product_id=self.packing_type_id.product_id.id
            self.price=self.packing_type_id.price
        else:
            self.product_id=False
            self.price=0




class BoxTemplate(models.Model):
    _name = "box.template"


    box_type_id = fields.Many2one('box.size',string="Box Type")
    price = fields.Float(related="product_id.list_price",string="Price",store=True)
    billing_type = fields.Many2one("billing.type",string="Billing Type")
    product_id = fields.Many2one('product.product',string="Product")

    @api.onchange('box_type_id','product_id')
    def onchange_box_type_id(self):
        if self.box_type_id:
            self.product_id=self.box_type_id.product_id.id
            self.price=self.box_type_id.price
        else:
            self.product_id=False
            self.price=0


class StorageTemplate(models.Model):
    _name = "storage.template"

    storage_sel_type = fields.Selection(related="billing_type.storage_type",store=True)
    
    storage_type = fields.Many2one('storage.type',domain="[('storage_type','=',storage_sel_type)]")
    price = fields.Float(related="product_id.list_price",string="Price",store=True)
    type = fields.Selection(related="storage_type.storage_type",store=True)
    billing_type = fields.Many2one("billing.type",string="Billing Type")
    product_id = fields.Many2one('product.product',string="Product")

    @api.onchange('storage_type','product_id')
    def onchange_storage_type(self):
        if self.storage_type:
            self.product_id=self.storage_type.product_id.id
            self.price=self.storage_type.price
        else:
            self.product_id=False
            self.price=0



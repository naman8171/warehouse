from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero



class StorageBox(models.Model):
    _name = 'storage.type'




    name = fields.Char("Name")

    storage_type_line = fields.One2many('storage.type.line','storage_type',string="Storage Type Lines")


    product_id = fields.Many2one("product.product",string="Product",required=True,domain=[('detailed_type','=','service')])
    price = fields.Float("Price",related="product_id.list_price",store=True)
    storage_type= fields.Selection([('Dedicated','Dedicated'),
                                    ('Shared','Shared')],required=True,string="Type",default='Shared')




class StorageBoxLine(models.Model):
    _name = 'storage.type.line'




    billing_type_id = fields.Many2one('billing.type',string="Billing Type" ,required=True)
    storage_type = fields.Many2one('storage.type')

    product_id = fields.Many2one("product.product",string="Product",required=True,domain=[('detailed_type','=','service')])
    price = fields.Float("Price",related="product_id.list_price",store=True)


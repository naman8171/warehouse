# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class PackingType(models.Model):
    _name = "thehub.packing.type"
    _order="display_name"


    def _get_name(self):
        name = super(PackingType, self)._get_name()
        return name


    def name_get(self):
        res = []
        for rec in self:
            if rec.packing_categ:
                name=rec.name+'( '+rec.packing_categ+" )"
            else:
                name=rec.name
            res.append((rec.id, name))
        return res

    @api.depends('name','packing_categ')
    def _compute_display_name(self):
        for rec in self:
            if rec.packing_categ:
                rec.display_name=rec.name+'( '+rec.packing_categ+" )"
            else:
                rec.display_name=rec.name

    display_name = fields.Char(compute="_compute_display_name",store=True)
    name = fields.Char('Name')
    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")
    price = fields.Float(related="product_id.list_price",store=True,string="Price")
    product_id = fields.Many2one("product.product",string='Product',required=True,domain=[('detailed_type','=','service')])
    packing_type = fields.Selection([('wro', 'WRO'),
                                    ('wo', 'WO')], string="Packing Related to",required=True)
    
    


class StockLocation(models.Model):
    _inherit = "stock.location"


    location_scan_name = fields.Char("Location Scan name")
    location_full = fields.Boolean('Location Full')
    billing_start = fields.Boolean('Billing Running')
    billing_date = fields.Date('Next Billing Date')
    partner_id = fields.Many2one('res.partner')
    storage_type_id = fields.Many2one("storage.type",string="Storage Type")
    storage_type = fields.Selection(related='storage_type_id.storage_type',store=True,string='Storage Type')

    

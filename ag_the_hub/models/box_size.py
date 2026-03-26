# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class BoxSize(models.Model):
    _name = "box.size"

    def name_get(self):
        res = []
        for rec in self:
            if rec.type:
                name=rec.name+'( '+rec.type+" )"
            else:
                name=rec.name
            res.append((rec.id, name))
        return res


    name = fields.Char('Name')
    price = fields.Float(related="product_id.list_price",store=True,string="Price")
    sequence = fields.Integer("Sequence")
    product_id = fields.Many2one("product.product",string='Product',required=True,domain=[('detailed_type','=','service')])
    type = fields.Selection([('box','Box'),
                            ('pallet','Pallet'),
                            ('floor','Floor')],string="Type")


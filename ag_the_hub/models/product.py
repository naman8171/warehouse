# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    platform = fields.Char("Platform", copy=False)
    color = fields.Char("Color")
    size = fields.Char("Size")
    gender = fields.Selection([('male','Male'),('female','Female'),('unisex','Unisex')],string="Gender")
    partner_id = fields.Many2one(related="responsible_id.partner_id",store=True)
    reorder_level = fields.Integer("Reorder Level")


class ProductProduct(models.Model):
    _inherit = "product.product"

    partner_id = fields.Many2one(related="responsible_id.partner_id",store=True)




    def get_product_data(self, product_ids):
        data = self.sudo().search_read(
            domain=[('id', 'in', product_ids[0])],
            fields=['id', 'name', 'default_code', 'platform']
        )
        return data

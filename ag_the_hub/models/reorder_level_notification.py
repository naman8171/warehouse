# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import date, timedelta


class ReorderLevelNotification(models.Model):
    _name = "reorder.level.notification"

    merchand_id = fields.Many2one('res.partner',string="Merchant")
    product_id = fields.Many2one('product.product',string="Product")
    old_reorder_level = fields.Float('Old Reorder Level')
    new_reorder_level=fields.Float('New Reorder Level')


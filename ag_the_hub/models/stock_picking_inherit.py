# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class StockPicking(models.Model):
    _inherit = "stock.picking"


    wro_id = fields.Many2one('warehouse.receive.order')
    wo_id = fields.Many2one('thehub.workorder')


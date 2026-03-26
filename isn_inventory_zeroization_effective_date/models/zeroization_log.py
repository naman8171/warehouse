from odoo import models, fields

class ZeroizationLog(models.Model):
    _name = 'inventory.zeroization.log'
    _description = 'Zeroization Log'
    _order = 'create_date desc'

    owner_id = fields.Many2one('res.partner', string='Owner')
    effective_date = fields.Date()
    create_date = fields.Datetime(readonly=True)
    line_ids = fields.One2many('inventory.zeroization.log.line', 'log_id', string='Details')


class ZeroizationLogLine(models.Model):
    _name = 'inventory.zeroization.log.line'
    _description = 'Zeroization Log Line'

    log_id = fields.Many2one('inventory.zeroization.log', string='Log')
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    old_quantity = fields.Float(string='Old Quantity')
    old_effective_date = fields.Date()

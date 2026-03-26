from odoo import models, fields

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # Add an index to the owner_id field.
    # The `index=True` attribute tells Odoo's ORM to create a database index for this field.
    owner_id = fields.Many2one(index=True)
    
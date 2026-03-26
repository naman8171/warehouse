# -*- coding: utf-8 -*-

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
	_inherit = "product.template"

	nonsku_product_line_id = fields.Many2one("approval.nonsku.product.line", string="Non-SKU Product Line")



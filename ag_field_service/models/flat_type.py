# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError, UserError

class FlatType(models.Model):
    _name = "flat.type"
    _description = "Flat Type"
    _order = "sequence"

    sequence = fields.Integer("Sequence")
    name = fields.Char("Flat Type")


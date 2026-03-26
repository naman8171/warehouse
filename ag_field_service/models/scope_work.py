# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError, UserError

class ScopeWork(models.Model):
    _name = "scope.work"
    _description = "Scope of Work"

    name = fields.Char("Scope of Work")


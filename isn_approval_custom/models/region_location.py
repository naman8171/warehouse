# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class RegionLocation(models.Model):
    _name = 'region.location'
    _description = "Region Location"
    
    name = fields.Char("Location Name")
    location_address = fields.Char("Address")
    branch_id = fields.Many2one('res.branch', string='Country Region')
    store_officer_id = fields.Many2one('res.users', string='Store Officer')
    account_rep_id = fields.Many2one('res.users', string='Account Rep')
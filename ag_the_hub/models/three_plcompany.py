# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class PlCompanies(models.Model):
    _name = "thehub.3plcompanies"

    name = fields.Char('Name')
    phone = fields.Char('Phone')
    email = fields.Char("Email")
    merchand_id = fields.Many2one('res.partner',string='Merchant',required=True)
    responsible_id = fields.Many2one('res.users',string="Responsible User")
    

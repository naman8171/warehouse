# -*- coding: utf-8 -*-

import logging
from odoo import models, fields


_logger = logging.getLogger(__name__)


class Branch(models.Model):
    _name = "res.branch"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Country Regions'
    _order = 'name'

    name = fields.Char(string='Name', required=True, store=True)
    company_id = fields.Many2one('res.company', required=True, string='Company')
    street = fields.Char("Street")
    street2 = fields.Char("Street2")
    zip = fields.Char("Zip")
    city = fields.Char("City")
    state_id = fields.Many2one(
        'res.country.state',
        string="State", domain="[('country_id', '=?', country_id)]"
    )
    country_id = fields.Many2one('res.country',  string="Country")
    email = fields.Char(string="Email", store=True, )
    phone = fields.Char(string="Phone", store=True)
    website = fields.Char(string="Website", readonly=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Branch name must be unique !')
    ]

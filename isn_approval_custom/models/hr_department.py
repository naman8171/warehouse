# -*- coding: utf-8 -*-
import logging
import traceback

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, ValidationError


class HrDepartment(models.Model):
    _inherit = "hr.department"
    
    account_ids = fields.Many2many('account.account',string='Allowed Accounts')
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    budget_max = fields.Monetary("Budget Max")
    


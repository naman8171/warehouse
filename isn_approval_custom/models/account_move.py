# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError



class AccountMove(models.Model):
    _inherit = 'account.move'
    
    isn_approval_id = fields.Many2one('approval.request', readonly=True, string='Approval')
    department_id = fields.Many2one('hr.department', copy=False)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    company_currency_id = fields.Many2one(related='currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
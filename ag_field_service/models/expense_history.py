# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ExpenseHistory(models.Model):
    _name = "expense.history"
    _description = "Expense History"

    partner_id = fields.Many2one("res.partner", string="Partner")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    date = fields.Date("Date")
    expense_amount = fields.Monetary("Amount")
    ref = fields.Char("Memo")
    # journal_id = fields.Many2one('account.journal', string="Journal")
    common_equipment_id = fields.Many2one("common.equipment", string="Common Equipment")

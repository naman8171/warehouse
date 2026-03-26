# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class ManagementFee(models.Model):
    _name = "management.fee"
    _description = 'Management Fee'

    @api.model
    def year_selection(self):
        select_year = 2021
        year_list = []
        while select_year <= fields.date.today().year:
            year_list.append((str(select_year), str(select_year)))
            select_year += 1
        return year_list

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    year = fields.Selection(selection=year_selection, string="Year")
    amount = fields.Monetary("Amount")
    branch_id = fields.Many2one("res.branch", string="Site")

    @api.constrains('branch_id', 'year')
    def _check_management_branch_year(self):
        for rec in self:
            management_fee_id = self.search([('id', '!=', rec.id), ('branch_id', '=', rec.branch_id.id), ('year', '=', rec.year)])
            if management_fee_id:
                raise ValidationError("Management Fee must be unique for each Site and Year!")

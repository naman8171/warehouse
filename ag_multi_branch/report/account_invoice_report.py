# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    """inherited invoice report"""
    _inherit = "account.invoice.report"

    branch_id = fields.Many2one('res.branch', 'Country Region', readonly=True)

    def _select(self):
        """select"""
        return super(AccountInvoiceReport, self)._select() + ", move.branch_id as branch_id"

    # def _group_by(self):
    #     """group by"""
    #     return super(AccountInvoiceReport, self)._group_by() + \
    #            ", move.branch_id"

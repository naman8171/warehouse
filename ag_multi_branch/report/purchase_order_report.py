# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseReport(models.Model):
    """inherited purchase report"""
    _inherit = "purchase.report"

    branch_id = fields.Many2one('res.branch', 'Country Region', readonly=True)

    def _select(self):
        """select"""
        return super(PurchaseReport, self)._select() + \
               ", spt.branch_id as branch_id"

    def _group_by(self):
        """group by"""
        return super(PurchaseReport, self)._group_by() + \
               ", spt.branch_id"

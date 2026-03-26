# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    branch_id = fields.Many2one('res.branch', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['branch_id'] = ", s.branch_id as branch_id"
        groupby += ', s.branch_id'
        return super(SaleReport, self)._query(with_clause, fields, groupby,
                                              from_clause)

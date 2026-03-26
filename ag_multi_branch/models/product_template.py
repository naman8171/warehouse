# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    """inherited product"""
    _inherit = 'product.template'

    branch_id = fields.Many2one("res.branch", string='Country Region', store=True,
                                readonly=False,
                                compute="_compute_branch")
    allowed_branch_ids = fields.Many2many('res.branch', string="Allowed Country Regions", compute='_compute_allowed_branch_ids')

    @api.depends('company_id')
    def _compute_allowed_branch_ids(self):
        for po in self:
            po.allowed_branch_ids = self.env.user.branch_ids.ids

    @api.depends('company_id')
    def _compute_branch(self):
        for order in self:
            company = self.env.company
            so_company = order.company_id if order.company_id else self.env.company
            branch_ids = self.env.user.branch_ids
            branch = branch_ids.filtered(
                lambda branch: branch.company_id == so_company)
            if branch:
                order.branch_id = branch.ids[0]
            else:
                order.branch_id = False

# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockWarehouse(models.Model):
    """inherited stock warehouse"""
    _inherit = "stock.warehouse"

    @api.model
    def _get_default_branch(self):
        """methode to get default branch"""
        branch_id = self.env.user.branch_id
        return branch_id

    def _get_branch_domain(self):
        """methode to get branch domain"""
        company = self.env.company
        branch_ids = self.env.user.branch_ids
        branch = branch_ids.filtered(
            lambda branch: branch.company_id == company)
        return [('id', 'in', branch.ids)]

    branch_id = fields.Many2one('res.branch', string='Country Region', store=True,
                                default=_get_default_branch,
                                domain=_get_branch_domain,
                                help='Leave this field empty if this warehouse '
                                     ' is shared between all branches')


class BranchStockMove(models.Model):
    """inherited stock.move"""
    _inherit = 'stock.move'

    branch_id = fields.Many2one('res.branch', readonly=True, store=True,
                                related='picking_id.branch_id')


class BranchStockMoveLine(models.Model):
    """inherited stock move line"""
    _inherit = 'stock.move.line'

    branch_id = fields.Many2one('res.branch', readonly=True, store=True,
                                related='move_id.branch_id')


class BranchStockValuationLayer(models.Model):
    """Inherited Stock Valuation Layer"""
    _inherit = 'stock.valuation.layer'

    branch_id = fields.Many2one('res.branch', readonly=True, store=True,
                                related='stock_move_id.branch_id')

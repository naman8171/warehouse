# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountAccount(models.Model):
    """inherited account account"""
    _inherit = "account.account"

    def _get_branch_domain(self):
        """methode to get branch domain"""
        company = self.env.company
        branch_ids = self.env.user.branch_ids
        branch = branch_ids.filtered(
            lambda branch: branch.company_id == company)
        return [('id', 'in', branch.ids)]

    branch_id = fields.Many2one('res.branch', string='Country Region', store=True,
                                domain=_get_branch_domain,
                                help='Leave this field empty if this account is'
                                     ' shared between all branches')

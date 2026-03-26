# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BranchPartner(models.Model):
    """inherited partner"""
    _inherit = "res.partner"

    branch_id = fields.Many2one("res.branch", string='Country Region', store=True,
                                readonly=False,
                                compute="_compute_branch")
    allowed_branch_ids = fields.Many2many('res.branch', string="Allowed Country Regions", compute='_compute_allowed_branch_ids')

    @api.depends('company_id')
    def _compute_allowed_branch_ids(self):
        for rec in self:
            rec.allowed_branch_ids = self.env.user.branch_ids.ids

    @api.depends('company_id')
    def _compute_branch(self):
        for rec in self:
            company = self.env.company
            so_company = rec.company_id if rec.company_id else self.env.company
            branch_ids = self.env.user.branch_ids
            branch = branch_ids.filtered(
                lambda branch: branch.company_id == so_company)
            if branch:
                rec.branch_id = branch.ids[0]
            else:
                rec.branch_id = False

    @api.model
    def default_get(self, default_fields):
        """Add the company of the parent as default if we are creating a
        child partner.Also take the parent lang by default if any, otherwise,
        fallback to default DB lang."""
        values = super().default_get(default_fields)
        parent = self.env["res.partner"]
        if 'parent_id' in default_fields and values.get('parent_id'):
            parent = self.browse(values.get('parent_id'))
            values['branch_id'] = parent.branch_id.id
        return values

    @api.onchange('parent_id', 'branch_id')
    def _onchange_parent_id(self):
        """methode to set branch on changing the parent company"""
        if self.parent_id:
            self.branch_id = self.parent_id.branch_id.id

    def write(self, vals):
        """override write methode"""
        if vals.get('branch_id'):
            branch_id = vals['branch_id']
            for partner in self:
                # if partner.child_ids:
                for child in partner.child_ids:
                    child.write({'branch_id': branch_id})
        else:
            for partner in self:
                # if partner.child_ids:
                for child in partner.child_ids:
                    child.write({'branch_id': False})
        result = super(BranchPartner, self).write(vals)
        return result

    def action_view_sale_order(self):
        pass

# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, timedelta

class TotalDistributionRatio(models.Model):
    _name = "total.distribution.ratio"
    _description = "Total Distribution Ratio"

    branch_id = fields.Many2one("res.branch", string="Site", copy=False)
    flat_type_id = fields.Many2one("flat.type", string="Type", copy=False)
    total_resident_count = fields.Integer("Total Resident Count", compute="_compute_tdr")
    factor = fields.Float("Factor", copy=False)
    total = fields.Float("Total", compute="_compute_tdr")

    @api.depends('flat_type_id', 'total_resident_count', 'factor')
    def _compute_tdr(self):
        for rec in self:
            if rec.flat_type_id:
                rec.total_resident_count = self.env['res.partner'].sudo().search_count([('branch_id', '=', rec.branch_id.id), ('contact_type', '=', 'Resident'), ('flat_type', '=', rec.flat_type_id.id), ('appartment_status', '!=', 'Consficated')])
                rec.total = rec.total_resident_count * rec.factor
            else:
                rec.total_resident_count = 0
                rec.total = 0

    @api.constrains('branch_id', 'flat_type_id')
    def _check_tdr_branch_type(self):
        for rec in self:
            tdr_id = self.search([('id', '!=', rec.id), ('branch_id', '=', rec.branch_id.id), ('flat_type_id', '=', rec.flat_type_id.id)])
            if tdr_id:
                raise ValidationError("TDR must be unique for each Site and type!")
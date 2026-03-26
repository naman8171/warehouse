# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, timedelta

class PowerCost(models.Model):
    _name = "power.cost"
    _description = "Power Cost"

    name = fields.Char("Name")
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, related="branch_id.currency_id")
    branch_id = fields.Many2one("res.branch", string="Site", copy=False)
    date = fields.Date("Date", copy=False)
    power_cost_line_ids = fields.One2many("power.cost.line", "power_cost_id", string="Power Cost Lines", copy=False)
    total_capu = fields.Float("Common Area Power Units", copy=False, compute="_compute_total_capc", store=True)
    total_capc = fields.Monetary("Common Area Power Cost", copy=False, compute="_compute_total_capc", store=True)

    @api.depends('power_cost_line_ids', 'power_cost_line_ids.total_power_cost', 'power_cost_line_ids.units')
    def _compute_total_capc(self):
        for rec in self:
            rec.total_capc = sum(rec.power_cost_line_ids.mapped('total_power_cost'))
            rec.total_capu = sum(rec.power_cost_line_ids.mapped('units'))

    @api.constrains('branch_id', 'date')
    def _check_power_cost(self):
        for rec in self:
            power_cost_id = self.search([('id', '!=', rec.id), ('branch_id', '=', rec.branch_id.id)])
            if power_cost_id:
                raise ValidationError("Power Cost must be unique for each Site !")

class PowerCostLine(models.Model):
    _name = "power.cost.line"
    _description = "Power Cost Line"

    name = fields.Char("Name")
    power_cost_id = fields.Many2one("power.cost", string="Power Cost", copy=False)
    branch_id = fields.Many2one("res.branch", string="Site", copy=False, related="power_cost_id.branch_id")
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, related="branch_id.currency_id")
    units = fields.Float("Units", copy=False)
    unit_price = fields.Monetary("Unit Price", copy=False)
    admin_vat = fields.Monetary("Admin Charges & Vat", copy=False)
    subtotal = fields.Monetary("Subtotal", copy=False, compute="_compute_total", store=True)
    total_power_cost = fields.Float("Total Power Cost", copy=False, compute="_compute_total", store=True)

    @api.depends('units', 'unit_price', 'admin_vat')
    def _compute_total(self):
        for rec in self:
            rec.subtotal = rec.units * rec.unit_price
            rec.total_power_cost = (rec.units * rec.unit_price) + rec.admin_vat

   

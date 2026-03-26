# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, timedelta

class ResBranch(models.Model):
    _inherit = "res.branch"

    store_user_ids = fields.Many2many('res.users', 'store_branch_rel', string='Store Officer')
    facility_manager_id = fields.Many2one('res.users', string='Facility Manager')
    resident_ids = fields.One2many("res.partner", "branch_id", string="Residents", compute="_compute_resident_ids")
    cost_entry_ids = fields.One2many("cost.entry", "branch_id", string="Cost Entries")
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    total_amount = fields.Monetary("Total Amount", compute="_compute_total_amount", store=True)
    tdr_ids = fields.One2many("total.distribution.ratio", "branch_id", string="Distribution Ratio")
    total_tdr = fields.Float("Total Amount", compute="_compute_total_tdr", store=True)
    common_area_cost_ids = fields.One2many("common.area.cost", 'branch_id', string="Common Area Cost", copy=False)
    power_cost_ids = fields.One2many("power.cost", "branch_id", string="Power Cost", copy=False)

    @api.depends('cost_entry_ids', 'cost_entry_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.cost_entry_ids.mapped('amount'))

    def _compute_resident_ids(self):
        for rec in self:
            rec.resident_ids = self.env['res.partner'].sudo().search([('contact_type', '=', 'Resident'), ('branch_id', '=', rec.id)])

    @api.depends('tdr_ids', 'tdr_ids.total')
    def _compute_total_tdr(self):
        for rec in self:
            rec.total_tdr = sum(rec.tdr_ids.mapped('total'))

    def _update_common_cost_area_expense(self):
        branch_ids = self.env['res.branch'].sudo().search([])
        current_month_year = datetime.now().strftime("%b-%Y")
        for branch_id in branch_ids:
            tcac = sum(branch_id.cost_entry_ids.filtered(lambda x: x.effective_date.strftime("%b-%Y") == current_month_year).mapped('amount'))
            tcapu = sum(branch_id.power_cost_ids.filtered(lambda x: x.date.strftime("%b-%Y") == current_month_year).mapped('total_capu'))
            tcapc = sum(branch_id.power_cost_ids.filtered(lambda x: x.date.strftime("%b-%Y") == current_month_year).mapped('total_capc'))
            total_tdr = branch_id.total_tdr
            if total_tdr:
                tcac_tdr = tcac/total_tdr
            else:
                tcac_tdr = False
            for line in branch_id.tdr_ids:
                common_area_cost_id = self.env['common.area.cost'].search([('flat_type_id', '=', line.flat_type_id.id), ('branch_id', '=', branch_id.id)])
                if len(common_area_cost_id) > 1:
                    common_area_cost_ids = common_area_cost_id
                    for common_area_cost_id in common_area_cost_ids:
                        if common_area_cost_id:
                            effective_date_month_year = common_area_cost_id.effective_date.strftime("%b-%Y")
                        else:
                            effective_date_month_year = False
                        if line.total_resident_count:
                            amt = tcac_tdr/line.total_resident_count
                            common_area_power_unit = (tcapu/line.total_resident_count) * line.factor
                            common_area_power_cost = (tcapc/line.total_resident_count) * line.factor
                        else:
                            amt = 0
                            common_area_power_cost = 0
                            common_area_power_unit = 0
                        if not common_area_cost_id or effective_date_month_year != current_month_year:
                            common_area_cost_id = self.env['common.area.cost'].create({
                                    'flat_type_id': line.flat_type_id.id,
                                    'currency_id': branch_id.currency_id.id,
                                    'effective_date': datetime.now(),
                                    'amount': amt,
                                    'branch_id': branch_id.id,
                                    'common_area_power_unit': common_area_power_unit,
                                    'common_area_power_cost': common_area_power_cost,
                                })
                            partner_ids = self.env['res.partner'].search([('flat_type', '=', line.flat_type_id.id), ('branch_id', '=', branch_id.id), ('contact_type', '=', 'Resident')])
                            for partner_id in partner_ids:
                                    expense_history_id = self.env['expense.history'].create({
                                        'partner_id': partner_id.id,
                                        'date': fields.date.today(),
                                        'expense_amount': amt,
                                        'ref': "Common Area Cost for %s Resident" %(line.flat_type_id.name),
                                    })
                                    expense_history_id = self.env['expense.history'].create({
                                        'partner_id': partner_id.id,
                                        'date': fields.date.today(),
                                        'expense_amount': common_area_power_cost,
                                        'ref': "Common Area Power Cost for %s Resident" %(line.flat_type_id.name),
                                    })
                else:
                    if common_area_cost_id:
                        effective_date_month_year = common_area_cost_id.effective_date.strftime("%b-%Y")
                    else:
                        effective_date_month_year = False
                    if line.total_resident_count:
                        amt = tcac_tdr/line.total_resident_count
                        common_area_power_unit = (tcapu/line.total_resident_count) * line.factor
                        common_area_power_cost = (tcapc/line.total_resident_count) * line.factor
                    else:
                        amt = 0
                        common_area_power_cost = 0
                        common_area_power_unit = 0
                    if not common_area_cost_id or effective_date_month_year != current_month_year:
                        common_area_cost_id = self.env['common.area.cost'].create({
                                'flat_type_id': line.flat_type_id.id,
                                'currency_id': branch_id.currency_id.id,
                                'effective_date': datetime.now(),
                                'amount': amt,
                                'branch_id': branch_id.id,
                                'common_area_power_unit': common_area_power_unit,
                                'common_area_power_cost': common_area_power_cost,
                            })
                        partner_ids = self.env['res.partner'].search([('flat_type', '=', line.flat_type_id.id), ('branch_id', '=', branch_id.id), ('contact_type', '=', 'Resident')])
                        for partner_id in partner_ids:
                                expense_history_id = self.env['expense.history'].create({
                                    'partner_id': partner_id.id,
                                    'date': fields.date.today(),
                                    'expense_amount': amt,
                                    'ref': "Common Area Cost for %s Resident" %(line.flat_type_id.name),
                                })
                                expense_history_id = self.env['expense.history'].create({
                                    'partner_id': partner_id.id,
                                    'date': fields.date.today(),
                                    'expense_amount': common_area_power_cost,
                                    'ref': "Common Area Power Cost for %s Resident" %(line.flat_type_id.name),
                                })

class CostEntry(models.Model):
    _name = "cost.entry"
    _description = "Cost Entries"

    partner_id = fields.Many2one("res.partner", string="Vendor")
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, related="branch_id.currency_id")
    cost_category_id = fields.Many2one("cost.category", string="Cost Category")
    amount = fields.Monetary("Amount")
    effective_date = fields.Datetime("Effective Date")
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    branch_id = fields.Many2one("res.branch", string="Site")

class CommonAreaCost(models.Model):
    _name = "common.area.cost"
    _description = "Common Area Cost"

    flat_type_id = fields.Many2one("flat.type", string="Type", copy=False)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, related="branch_id.currency_id")
    effective_date = fields.Datetime("Effective Date")
    amount = fields.Monetary("Amount")
    common_area_power_unit = fields.Float("Common Area Power Units", copy=False)
    common_area_power_cost = fields.Monetary("Common Area Power Cost", copy=False)
    branch_id = fields.Many2one("res.branch", string="Site")

class CommonAreaPowerCost(models.Model):
    _name = "common.area.power.cost"
    _description = "Common Area Power Cost"

    # flat_type_id = fields.Many2one("flat.type", string="Type", copy=False)
    # currency_id = fields.Many2one('res.currency', string="Currency", readonly=True )
    # effective_date = fields.Datetime("Effective Date")
    # amount = fields.Monetary("Amount")
    # branch_id = fields.Many2one("res.branch", string="Site")

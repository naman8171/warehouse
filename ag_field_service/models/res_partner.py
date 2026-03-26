# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"
    _order = "sequence asc"

    sequence = fields.Integer("Sequence", copy=False)
    contact_type = fields.Selection([('Resident', 'Resident'), ('Vendor', 'Vendor')], string="Contact Type", copy=False)
    # site_id = fields.Char(string='Site', copy=False)
    appartment_status = fields.Selection([('Vacant', 'Vacant'), ('Occupied', 'Occupied'), ('Consficated', 'Consficated')], string="Apartment Status", copy=False)
    residence_type = fields.Selection([('Landlord', 'Landlord'), ('Tenant', 'Tenant')], string="Residence Type", copy=False)
    landlord_name = fields.Char("Landlord Name", copy=False)
    landlord_contact = fields.Char("Landlord Contact", copy=False)
    landlord_email = fields.Char("Landlord Email", copy=False)
    tenant_name = fields.Char("Tenant Name", copy=False)
    tenant_contact = fields.Char("Tenant Contact", copy=False)
    tenant_email = fields.Char("Tenant Email", copy=False)
    next_kin = fields.Char("Next of Kin", copy=False)
    flat_type = fields.Many2one("flat.type", string="Flat Type", copy=False)
    resident_commencement_date = fields.Date("Resident Commencement Date", copy=False)
    resident_end_date = fields.Date("Resident End Date", copy=False)
    total_available_amount = fields.Float("Available Amount", compute="_compute_total_available_amount")
    block = fields.Char("Block")
    flat_no = fields.Integer("Flat Number")
    intercom_no = fields.Integer(" Intercom Number")
    deposit_history_ids = fields.One2many("deposit.history", "partner_id", string="Deposit History", copy=False)
    expense_history_ids = fields.One2many("expense.history", "partner_id", string="Expense History", copy=False)
    meter_reading_ids = fields.One2many("meter.reading", "partner_id", string="Meter Readings", copy=False)

    def action_exit(self):
        pass

    def _compute_total_available_amount(self):
        for rec in self:
            deposit_amount = 0
            expense_amount = 0
            if rec.deposit_history_ids:
                deposit_amount = sum(rec.deposit_history_ids.mapped('deposit_amount'))
            if rec.expense_history_ids:
                expense_amount = sum(rec.expense_history_ids.mapped('expense_amount'))
            rec.total_available_amount = deposit_amount - expense_amount


    def open_action_followup(self):
        self.ensure_one()
        pass

class DepositHistory(models.Model):
    _name = "deposit.history"
    _description = "Deposit History"

    partner_id = fields.Many2one("res.partner", string="Partner")
    currency_id = fields.Many2one('res.currency', related="partner_id.currency_id", string="Currency", readonly=True)
    payment_id = fields.Many2one('account.payment', string="Payment")
    date = fields.Date("Date")
    deposit_amount = fields.Monetary("Amount")
    ref = fields.Char("Memo")
    journal_id = fields.Many2one('account.journal', string="Journal")

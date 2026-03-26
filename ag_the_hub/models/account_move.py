# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountMove(models.Model):
	_inherit = "account.move"

	billing_period_start = fields.Date("Billing Period Start")
	billing_period_end = fields.Date("Billing Period End")
	billing_type = fields.Char("Billing Type")
# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

class ManagementFee(models.Model):
    _inherit = "management.fee"

    def _update_cost_entries_management_fee(self):
        year = datetime.now().year
        site_ids = self.env['res.branch'].sudo().search([])
        for site in site_ids:
            management_fee_id = self.search([('branch_id', '=', site.id), ('year', '=', year)], limit=1)
            cost_category_id = self.env['cost.category'].search([('name', '=', 'Management Fee')])
            if not cost_category_id:
                cost_category_id = self.env['cost.category'].create({
                                                    'name': 'Management Fee'
                                                })
            if management_fee_id:
                cost_entry_id = self.env['cost.entry'].sudo().search([('cost_category_id', '=', cost_category_id.id), ('branch_id', '=', site.id)])
                current_month_year = datetime.now().strftime("%b-%Y")
                if cost_entry_id:
                    effective_date_month_year = cost_entry_id.effective_date.strftime("%b-%Y")
                else:
                    effective_date_month_year = False
                if not cost_entry_id or effective_date_month_year != current_month_year:
                    cost_entry_id = self.env['cost.entry'].create({
                            'partner_id': False,
                            'currency_id': self.currency_id.id,
                            'cost_category_id': cost_category_id.id,
                            'amount': (management_fee_id.amount/12),
                            'effective_date': datetime.now(),
                            'purchase_id': False,
                            'branch_id': site.id
                        })

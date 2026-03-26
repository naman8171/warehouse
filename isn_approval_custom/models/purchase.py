# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    location = fields.Many2one("region.location", string="Location", copy=False)
    department_id = fields.Many2one('hr.department', copy=False)

    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        for rec in self.invoice_ids:
            rec.department_id = self.department_id.id
        return res
    
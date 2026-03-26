# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_department(self):
        if self.purchase_id and self.purchase_id.department_id:
            return self.purchase_id.department_id.id
        else:
            return False

    approval_request_id = fields.Many2one("approval.request", string="Approval Request", copy=False)
    department_id = fields.Many2one('hr.department', copy=False, related="purchase_id.department_id", store=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments", copy=False)

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    location = fields.Many2one("region.location", string="Location", copy=False)

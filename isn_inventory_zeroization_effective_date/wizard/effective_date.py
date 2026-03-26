from odoo import models, fields, api

class EffectiveDateWizard(models.TransientModel):
    _name = 'inventory.effective.date.wizard'
    _description = 'Inventory Zeroization Wizard'

    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today)

    def action_cascade_effective_date(self):
        self.ensure_one()
        quants = self.env['stock.quant'].browse(self.env.context.get('active_ids'))
        for quant in quants:
            quant.inventory_date = self.effective_date
        return {'type': 'ir.actions.act_window_close'}

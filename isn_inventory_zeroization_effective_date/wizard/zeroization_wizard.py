from odoo import models, fields, api, _

class ZeroizationWizard(models.TransientModel):
    _name = 'inventory.zeroization.wizard'
    _description = 'Inventory Zeroization Wizard'

    owner_id = fields.Many2one('res.partner', string='Owner', required=True)
    allowed_owner_ids = fields.Many2many('res.partner', string='Allowed Owners', compute='_compute_allowed_owners')
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today)
    # affected_product_ids = fields.Many2many('product.product', compute='_compute_affected_products', readonly=True)

    @api.depends('effective_date')
    def _compute_allowed_owners(self):
        owner_ids = self.env['stock.quant'].read_group(
            [('owner_id', '!=', False)],
            ['owner_id'],
            ['owner_id']
        )
        owner_ids = [res['owner_id'][0] for res in owner_ids if res['owner_id']]
        for rec in self:
            rec.allowed_owner_ids = [(6, 0, owner_ids)]

    def action_zeroize_stock(self):
        self.ensure_one()

        # Find the stock quants to be zeroized.
        # Searching for quants with quantity > 0 is good practice to avoid unnecessary updates.
        quants = self.env['stock.quant'].search([
            ('owner_id', '=', self.owner_id.id)
        ])

        # Create a single log entry for the entire operation.
        log = self.env['inventory.zeroization.log'].create({
            'owner_id': self.owner_id.id,
            'effective_date': self.effective_date,
        })

        # Prepare a list of dictionaries for bulk creation of log lines.
        log_line_vals_list = []
        for quant in quants:
            log_line_vals_list.append({
                'log_id': log.id,
                'product_id': quant.product_id.id, # Using product_id from quant
                'location_id': quant.location_id.id,
                'old_quantity': quant.quantity,
                'old_effective_date': quant.inventory_date,
            })

        # Bulk create all log lines with a single database insert.
        self.env['inventory.zeroization.log.line'].create(log_line_vals_list)

        # Bulk update all found quants to zero.
        # This is far more efficient than iterating and updating one by one.
        quants.write({
            'quantity': 0,
            'inventory_date': self.effective_date,
        })

        # Return a message or action to the user to confirm success.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Inventory Zeroized'),
                'message': _('Successfully zeroized stock records for %s.') % (self.owner_id.name),
                'sticky': True,
            }
        }

    # @api.depends('owner_id')
    # def _compute_affected_products(self):
    #     for wizard in self:
    #         if not wizard.owner_id:
    #             wizard.affected_product_ids = [(6, 0, [])]
    #             continue

    #         results = self.env['stock.quant'].read_group(
    #             [('owner_id', '=', wizard.owner_id.id)],
    #             ['product_id'],
    #             ['product_id']
    #         )
    #         product_ids = [res['product_id'][0] for res in results if res['product_id']]
    #         wizard.affected_product_ids = [(6, 0, product_ids)]

    # def action_zeroize_stock(self):
    #     self.ensure_one()
    #     log_vals = {
    #         'owner_id': self.owner_id.id,
    #         'effective_date': self.effective_date,
    #     }
    #     log = self.env['inventory.zeroization.log'].create(log_vals)
    #     quants = self.env['stock.quant'].search([
    #         ('owner_id', '=', self.owner_id.id), ('quantity','>', 0)
    #     ])
    #     print("**********", self.owner_id.name, len(quants))
    #     eeeeeeeeeeee
    #     for quant in quants:
    #         self.env['inventory.zeroization.log.line'].create({
    #             'log_id': log.id,
    #             'product_id': product.id,
    #             'location_id': quant.location_id.id,
    #             'old_quantity': quant.quantity,
    #             'old_effective_date': quant.inventory_date,
    #         })
    #         quant.quantity = 0
    #         quant.inventory_date = self.effective_date

    #     return {'type': 'ir.actions.act_window_close'}

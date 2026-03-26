
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime

class AddPackaging(models.Model):
    _name = "add.packaging"
    _description = "Add Packaging"


    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")
    packing_type_id = fields.Many2one('thehub.packing.type',domain="[('packing_categ', '=', packing_categ),('packing_type','=','wo')]")

    available_product_lines = fields.One2many('add.packaging.lines','add_package_id')
    selected_line_ids = fields.Many2many('thehub.workorder.lines', string="Selected Lines")
    wo_id = fields.Many2one('thehub.workorder')
    address = fields.Text('Address',required=True)
    weight=fields.Float('Weight',required=True)
    wo_line_products_ids = fields.Many2many("product.product", "wo_line_product_rel", string="WO Line Products", compute="_compute_wo_line_products_ids")
    product_ids = fields.Many2many("product.product", "add_package_product_rel", string="Select Products To Add Line")

    @api.depends('wo_id')
    def _compute_wo_line_products_ids(self):
        for rec in self:
            if rec.wo_id:
                wo_line_ids = rec.wo_id.wo_line_ids - rec.wo_id.package_lines.mapped('product_lines')
                rec.wo_line_products_ids = wo_line_ids.mapped("product_id").ids


    @api.onchange('selected_line_ids')
    def _onchange_product_ids(self):
        self.available_product_lines = [(5, 0, 0)]  # Clear existing lines
        if self.selected_line_ids:
            new_lines = []
            filtered_lines = self.wo_id.wo_line_ids.filtered(
                lambda l: l.id in self.selected_line_ids.ids
            )
            for line in filtered_lines:
                new_lines.append((0, 0, {
                    'wo_line': line.id
                }))
                # available_product_lines = self.wo_id.wo_line_ids.filtered(lambda l: str(l.product_id.id) in str(product.id))
                # for line in available_product_lines:
                #     new_lines.append((0, 0, {
                #         'wo_line':line.id
                #     }))
            self.available_product_lines = new_lines

    @api.onchange('product_ids')
    def _onchange_partner_id(self):
        if self.product_ids:
            wo_lines = []
            available_lines = self.wo_id.wo_line_ids.filtered(lambda l: l.product_id.id in self.product_ids.ids) - self.wo_id.package_lines.mapped('product_lines')
            # for product in self.product_ids:
            #     available_product_lines = self.wo_id.wo_line_ids.filtered(lambda l: str(l.product_id.id) in str(product.id))
            for line in available_lines:
                wo_lines.append(line.id)
            domain = [('id', 'in', wo_lines)]
        else:
            domain = [('id', 'in', self.wo_id.wo_line_ids.ids)]
        return {'domain': {'selected_line_ids': domain}}


    
    def add_package_pack(self):
        # line_ids =[]
        # for line in self.available_product_lines:
        #     if line.select:
        #         line_ids.append(line.wo_line.id)
        if self.weight == 0 or self.weight < 0:
            raise ValidationError("Please enter a weight greater than zero.")
        line_ids = self.available_product_lines.mapped('wo_line').ids
        if len(line_ids)>0:
            self.env['thehub.workorder.lines.package'].sudo().create({
                'packing_categ':self.packing_categ,
                'packing_type_id':self.packing_type_id.id,
                'product_lines':[(6,0,line_ids)],
                'address':self.address,
                'wo_id':self.wo_id.id,
                'weight':self.weight
                })


class AddPackagingLines(models.Model):
    _name = "add.packaging.lines"
    _description = "Add Packaging Lines"

    wo_line = fields.Many2one('thehub.workorder.lines')
    select = fields.Boolean('Select')

    product_id = fields.Many2one(related="wo_line.product_id", string="Product")
    product_qty = fields.Float(related="wo_line.product_qty",string="Quantity")
    send_as = fields.Selection(related="wo_line.send_as", string="Send As")
    package_id = fields.Many2one(related="wo_line.package_id",string="Package")
    add_package_id = fields.Many2one('add.packaging')




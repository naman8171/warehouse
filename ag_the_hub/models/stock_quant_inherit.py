from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero


import base64
import xlwt
import io
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class StockQuant(models.Model):
    _inherit = 'stock.quant'
    _rec_name = 'display_name'



    def export_inventory_list(self,data):
        IrConfig = self.env['ir.config_parameter'].sudo()

        base_url = IrConfig.get_param('web.base.url')

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sale_By_Vendor_Report')
        worksheet.col(3).width = int(50 * 260)
        worksheet.col(4).width = int(30 * 260)
        worksheet.col(5).width = int(18 * 260)
        worksheet.col(6).width = int(18 * 260)
        worksheet.col(7).width = int(18 * 260)
        worksheet.col(8).width = int(18 * 260)
        worksheet.col(9).width = int(18 * 260)

        row = 0
        worksheet.write_merge(row, row + 1, 0, 7, 'Inventory Status', xlwt.easyxf('font:bold on;alignment: horizontal  center;'))
        row += 2
        row += 3

        worksheet.write(row, 3, 'Product Name', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 4, 'Product SKU', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 5, 'Product Barcode', xlwt.easyxf('font:bold on'))
        worksheet.write(row, 6, 'On Hand', xlwt.easyxf('font:bold on'))
        
        worksheet.write(row, 7, 'Reorder Level', xlwt.easyxf('font:bold on'))

        row += 1
        # total_qty=0
        # total_price=0
        # stock_quant_ids = self.env['stock.quant'].sudo().search([('id','in',data)])
        if len(data) > 0:
            # for line in data:
            #     worksheet.write(row, 3, line[1])
            #     worksheet.write(row, 4, line[2])
            #     worksheet.write(row, 5, line[3])
            #     worksheet.write(row, 6, line[4])
            #     worksheet.write(row, 7, line[5])
                
                
            #     row += 1
            product_domain = [('id', 'in', data)]
        else:
            inventory_env = self.env['stock.quant'].sudo()
            partner_id = self.env.user.partner_id.id
            domain = [
                ('owner_id', '=', partner_id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
                ('product_id.active', '=', True)
            ]
            inventory_records = inventory_env.search(domain)
            product_domain = [('id', 'in', inventory_records.mapped('product_id').ids)]
            # Fetch product data with pagination
        product_ids = self.env['product.product'].sudo().search(
            product_domain, order="id")
        # Prepare inventory data for the template
        inventory_data = []
        for product in product_ids:
            # product_quantities = inventory_env.search([
            #     ('owner_id', '=', partner_id),
            #     ('quantity', '>', 0),
            #     ('product_id', '=', product.id)
            # ])

            # total_quantity = sum(
            #     quant.quantity - quant.reserved_quantity
            #     for quant in product_quantities
            #     if (quant.quantity - quant.reserved_quantity) > 0
            # )
            # total_quantity = sum(product_quantities.mapped('quantity'))
            worksheet.write(row, 3, product.name or None)
            worksheet.write(row, 4, product.default_code or None)
            worksheet.write(row, 5, product.barcode or None)
            worksheet.write(row, 6, product.qty_available)
            worksheet.write(row, 7, product.reorder_level)                
            
            row += 1

        # worksheet.write(row, 3, 'Total')
        # worksheet.write(row, 4, str("{:.2f}".format(total_qty)))
        # worksheet.write(row, 5, str("{:.2f}".format(total_price)))



        # worksheet.write(row, 0, 'Grand Totals', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 1, str(data.get('total_amount')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 2, '', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 3, str(data.get('total_qty')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 4, str(data.get('total_sales')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 5, '', xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 6, str(data.get('total_gross_profit')), xlwt.easyxf('font:bold on'))
        # worksheet.write(row, 7, '', xlwt.easyxf('font:bold on'))
        # row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        new_file_id = self.env['wizard.update.quantity'].sudo().create({
            'file':base64.encodebytes(fp.getvalue()),
            'filename':'inventory_stock.xls'
            })
        complete_url = '%s/web/content/?model=wizard.update.quantity&field=file&download=true&id=%s&filename=%s' % (base_url,new_file_id.id, new_file_id.filename)
        return complete_url



    display_name = fields.Char(compute='_compute_display_name_custom')
    wro_id = fields.Many2one("warehouse.receive.order",store=True,compute="_compute_workorder_receive")
    consolidated_type = fields.Selection([('consolidated', 'Consolidated'),
                                ('non_consolidated', 'Non-Consolidated'),
                                ], string="Consolidated Type", copy=False,compute="_compute_workorder_receive",store=True)
    
    @api.depends('lot_id','product_id')
    def _compute_display_name_custom(self):
        for record in self:
            record.display_name = '%s-%s' % (record.lot_id.name if record.lot_id else '', record.product_id.name)


    @api.depends('lot_id')
    def _compute_workorder_receive(self):
        for quant in self:
            package_id = self.env['single.sku.per.box.line'].sudo().search([('package_number','=',quant.lot_id.name)])
            if not package_id:
                package_id = self.env['single.sku.per.box.product.line'].sudo().search([('package_number','=',quant.lot_id.name)])
                if not package_id:
                    package_id = self.env['single.sku.per.pallet.line'].sudo().search([('package_number','=',quant.lot_id.name)])
                    if not package_id:
                        wro_id=False
                        consolidated_type=False
                    else:
                        wro_id=package_id.wro_single_sku_per_pallet_id.wro_id
                        consolidated_type=package_id.wro_single_sku_per_pallet_id.consolidated_type

                else:
                    if package_id.wro_single_sku_per_box_line_id:
                        wro_id=package_id.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id
                        consolidated_type=package_id.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.consolidated_type
                    elif package_id.wro_single_sku_per_pallet_line_id:
                        wro_id=package_id.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id
                        consolidated_type = package_id.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.consolidated_type
                    

            else:
                wro_id=package_id.wro_single_sku_per_box_id.wro_id
                consolidated_type=package_id.wro_single_sku_per_box_id.consolidated_type
            quant.wro_id=wro_id
            quant.consolidated_type=consolidated_type



    def get_product_data(self, product_ids):
        stock_quant_list=[]
        stock_quants = self.sudo().search([('id', 'in', product_ids[0])])
        for quant in stock_quants:
            package_id = self.env['single.sku.per.box.line'].sudo().search([('package_number','=',quant.lot_id.name)])
            if not package_id:
                package_id = self.env['single.sku.per.box.product.line'].sudo().search([('package_number','=',quant.lot_id.name)])
                if not package_id:
                    package_id = self.env['single.sku.per.pallet.line'].sudo().search([('package_number','=',quant.lot_id.name)])
                    if not package_id:
                        raise ValidationError('Package Number Not found')
            stock_quant_list.append({
                'id':quant.id,
                'name':quant.display_name,
                'available_quantity':quant.quantity,
                'lot_number':quant.lot_id.name,
                'lot_id':quant.lot_id.id,
                'consolidated_type':package_id.send_as,
                'package_number':quant.lot_id.name,

                })

            
        return stock_quant_list

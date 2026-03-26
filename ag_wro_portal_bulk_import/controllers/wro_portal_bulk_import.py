import base64
import binascii
import tempfile

import xlrd
from io import BytesIO

from odoo import _
from odoo.exceptions import UserError
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import content_disposition
from odoo.tools.misc import xlwt


class WroPortalBulkImport(CustomerPortal):

    @route(['/wro/download/sample/template'], type='http', auth='user', website=True)
    def wro_download_sample_template(self, **kw):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet', cell_overwrite_ok=True)
        worksheet.row(0).height = 10 * 50
        worksheet.col(0).width = 100 * 50
        worksheet.col(1).width = 100 * 50
        worksheet.col(2).width = 100 * 50
        worksheet.col(3).width = 100 * 50
        worksheet.col(4).width = 100 * 50
        worksheet.col(5).width = 100 * 100
        worksheet.col(6).width = 100 * 50
        worksheet.col(9).width = 100 * 100
        worksheet.col(10).width = 100 * 100

        header_style = xlwt.easyxf('font: bold on, height 250; align: wrap on, vert center, horiz center;')
        worksheet.write(0, 0, 'Product SKU', header_style)
        worksheet.write(0, 1, 'Shipment QTY', header_style)
        worksheet.write(0, 2, 'QTY Per Package', header_style)
        worksheet.write(0, 3, 'No Of Packages', header_style)
        worksheet.write(0, 4, 'Package Value', header_style)
        worksheet.write(0, 5, 'Consolidated Type', header_style)
        worksheet.write(0, 6, 'Location', header_style)
        worksheet.write(18, 9, 'Consolidate Type', header_style)
        worksheet.write(18, 10, 'consolidated', header_style)
        worksheet.write(19, 10, 'non_consolidated', header_style)

        file_data = BytesIO()
        workbook.save(file_data)
        file_data.seek(0)
        return request.make_response(
            file_data.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('sample_wro_report.xls')),
            ],
        )

    @route(['/import/new/wro'], type='http', auth='user', website=True)
    def import_new_wro(self, **kw):
        if not kw.get('att'):
            raise UserError('Please upload file first')
        if not kw.get('shipping_type'):
            raise UserError('Please select shipping type')

        wro_id = request.env['warehouse.receive.order'].sudo().create({
            'merchand_id': int(kw.get('merchand_id')),
            'warehouse_id': int(kw.get('warehouse_id')),
            'shipping_type': kw.get('shipping_type'),
            'inventory_type_parcel': 'single' if kw.get('shipping_type') == 'parcel' else False,
            'inventory_type_pallet': 'single' if kw.get('shipping_type') == 'pallet' else False,
            'pickup_method': kw.get('pickup_method'),
            'arrival_date': kw.get('arrival_date') or False,
            'third_party_ref': kw.get('third_party_ref'),
            'status': False,
        })

        file_content = base64.b64encode(kw.get('att').read())
        fp = tempfile.NamedTemporaryFile(suffix='.xlsx')
        fp.write(binascii.a2b_base64(file_content))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)

        product_list = []
        location_list = []
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                continue
            line = list(map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
            if not line[0]:
                continue

            product_id = request.env['product.product'].sudo().search([
                ('default_code', '=', line[0]),
                '|',
                ('partner_id', '=', wro_id.merchand_id.id),
                ('partner_id.child_ids', 'in', wro_id.merchand_id.ids),
            ], limit=1)
            location_id = request.env['stock.location'].sudo().search([
                ('location_scan_name', '=', line[6]),
                ('location_full', '!=', True),
            ], limit=1)

            if not product_id:
                product_list.append(line[0])
                continue
            if line[6] and not location_id:
                location_list.append(line[6])
                continue

            if wro_id.shipping_type == 'parcel':
                data = {
                    'product_id': product_id.id,
                    'product_qty': int(float(line[1])),
                    'qty_per_box': int(float(line[2])),
                    'no_of_boxes': int(float(line[3])),
                    'package_value': float(line[4]) if line[4] else 0.0,
                    'consolidated_type': line[5],
                    'is_default_location': True if location_id.id else False,
                    'defaultlocation_id': location_id.id if location_id else False,
                }
                wro_id.write({'wro_single_sku_per_box_ids': [(0, 0, data)]})
            elif wro_id.shipping_type == 'pallet':
                data = {
                    'product_id': product_id.id,
                    'product_qty': int(float(line[1])),
                    'qty_per_pallet': int(float(line[2])),
                    'no_of_pallets': int(float(line[3])),
                    'package_value': float(line[4]) if line[4] else 0.0,
                    'consolidated_type': line[5],
                    'is_default_location': True if location_id.id else False,
                    'defaultlocation_id': location_id.id if location_id else False,
                }
                wro_id.write({'wro_single_sku_per_pallet_ids': [(0, 0, data)]})

        if product_list:
            wro_id.message_post(body=_('<div>Below List Of product Not found in system related to merchant please review </div><div> %s </div>', str(product_list)))
        if location_list:
            wro_id.message_post(body=_('<div>Below List Of Location Not found in system related to merchant please review </div><div> %s </div>', str(location_list)))

        return request.redirect('/my/wros')


from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime
from odoo.exceptions import ValidationError, AccessError, MissingError, UserError, AccessDenied
from odoo.http import content_disposition, Controller, request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools.misc import xlwt
from odoo.http import request, content_disposition
import base64
import xlrd
import tempfile
import binascii
import io
import pandas as pd
from lxml import etree
import logging
from io import BytesIO
_logger = logging.getLogger(__name__)

import time
try:
    # For Python 3.3+
    time.clock = time.time
except AttributeError:
    pass

class BulkImportLines(models.TransientModel):
    _name = "bulk.import.lines"
    _description = "Bulk Import"



    file = fields.Binary('File')
    filename = fields.Char('File Name')
    wro_id = fields.Many2one('warehouse.receive.order')
    wo_id = fields.Many2one('thehub.workorder')


    def file_format_download_wo(self):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet', cell_overwrite_ok=True)
        worksheet.row(0).height = 10 * 50
        worksheet.col(0).width = 100 * 50
        worksheet.col(1).width = 100 * 50
        worksheet.col(2).width = 100 * 50
        worksheet.col(3).width = 100 * 50
        worksheet.col(4).width = 100 * 100
        worksheet.col(5).width = 100 * 100
        worksheet.col(6).width = 100 * 50
        worksheet.col(7).width = 100 * 100
        worksheet.col(8).width = 100 * 100
        worksheet.col(9).width = 100 * 100
        
        
        ###################  STYLES ###############################
        header_style = xlwt.easyxf("font: bold on, height 250; align: wrap on, vert center, horiz center;")
        
        plain = xlwt.easyxf()
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        ########################### EXCEL SHEET ##################################
        worksheet.write(0,0, 'Product SKU', header_style)
        worksheet.write(0,1, 'Transfer QTY', header_style)
        worksheet.write(0,2, 'Delivery Address', header_style)
        worksheet.write(0,3, 'Weight', header_style)
        worksheet.write(0,4, 'Consolidated Type', header_style)
        worksheet.write(0,5, 'Stock Type', header_style)
        worksheet.write(0,6, 'Location Name', header_style)
        worksheet.write(0,7, 'Package Name', header_style)
        
        
        worksheet.write(18,9, 'Consolidate Type', header_style)
        worksheet.write(18,10, 'consolidated', header_style)
        worksheet.write(19,10, 'non_consolidated', header_style)


        worksheet.write(20,9, 'Stock Type', header_style)
        worksheet.write(20,10, 'LIFO', header_style)
        worksheet.write(21,10, 'FIFO', header_style)
        # worksheet.write(20,10, 'unisex', header_style)
        file_data = BytesIO()
        workbook.save(file_data)
        record=self.create({
            
            'file': base64.encodebytes(file_data.getvalue()),
            'filename': 'sample_report.xls'
        })

        return {
        'type': 'ir.actions.act_url',
        'name': 'contract',
        'url': '/web/content/bulk.import.lines/%s/file/sample_report.xls?download=true' %(record.id),

    }


    def file_format_download(self):
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
        
        
        ###################  STYLES ###############################
        header_style = xlwt.easyxf("font: bold on, height 250; align: wrap on, vert center, horiz center;")
        
        plain = xlwt.easyxf()
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'

        ########################### EXCEL SHEET ##################################
        worksheet.write(0,0, 'Product SKU', header_style)
        worksheet.write(0,1, 'Shipment QTY', header_style)
        if self.wro_id.shipping_type == 'parcel':
            worksheet.write(0,2, 'QTY Per BOX', header_style)
            worksheet.write(0,3, 'No Of Boxes', header_style)
        else:
            worksheet.write(0,2, 'QTY Per Pallet', header_style)
            worksheet.write(0,3, 'No Of Pallet', header_style)
        worksheet.write(0,4, 'Package Value', header_style)
        worksheet.write(0,5, 'Consolidated Type', header_style)
        worksheet.write(0,6, 'Location', header_style)

        worksheet.write(18,9, 'Consolidate Type', header_style)
        worksheet.write(18,10, 'consolidated', header_style)
        worksheet.write(19,10, 'non_consolidated', header_style)
        # worksheet.write(20,10, 'unisex', header_style)
        file_data = BytesIO()
        workbook.save(file_data)
        record=self.create({
            
            'file': base64.encodebytes(file_data.getvalue()),
            'filename': 'sample_report.xls'
        })

        return {
        'type': 'ir.actions.act_url',
        'name': 'contract',
        'url': '/web/content/bulk.import.lines/%s/file/sample_report.xls?download=true' %(record.id),

    }


    def bulk_import_wo(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file)) # self.xls_file is your binary field
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        product_list=[]
        stock_not_list=[]
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(map(
                                lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                    row.value), sheet.row(row_no)))
                # in above line variable,
                if line[0]:
                    product_id = self.env['product.product'].search([('default_code','=',line[0]),'|', ('partner_id','=',self.wo_id.merchand_id.id), ('partner_id.child_ids','in',self.wo_id.merchand_id.ids)],limit=1)
                    if not product_id:
                        product_list.append(line[0])
                        continue

                    if line[5] == 'LIFO':
                        stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids','in',self.wo_id.merchand_id.ids),('location_id.usage','=','internal'),('product_id','=',product_id.id),('consolidated_type','=',line[4])],order='create_date desc')
                    else:
                        stock_product = self.env['stock.quant'].sudo().search(['|', ('owner_id','=',self.wo_id.merchand_id.id), ('owner_id.child_ids','in',self.wo_id.merchand_id.ids),('location_id.usage','=','internal'),('product_id','=',product_id.id)],order='create_date asc') #,('consolidated_type','=',line[4])
                    total_qty =0
                    quant_ids =[]
                    total_qty=0
                    location_ids=[]
                    total_qty =0
                    stock_available_qty=0
                    for quant in stock_product:
                        quantity=quant.quantity - quant.reserved_quantity
                        if quantity>0:
                            stock_available_qty+=quantity

                    if stock_available_qty<float(line[1]):
                        stock_not_list.append(line[0])
                        continue
                    for quant in stock_product:
                        quantity=quant.quantity - quant.reserved_quantity
                        if quantity>0 and float(line[1])>total_qty:
                            total_qty+=quantity
                            quant_ids.append(quant.id)
                            location_ids.append(quant.location_id.id)
                    required_quantity=float(line[1])
                    for quant in quant_ids:
                        stock_product = self.env['stock.quant'].sudo().browse(quant)
                        required_quantity=float(line[1])
                        required_quantity=required_quantity-(stock_product.quantity - stock_product.reserved_quantity)
                        qty=0
                        if required_quantity>0:
                            qty=stock_product.quantity - stock_product.reserved_quantity
                        else:
                            qty=float(line[1])


                        self.wo_id.write({'wo_line_ids':[(0,0,{
                        'package_id':stock_product.lot_id.id,
                        'product_qty':qty,
                        'product_id': product_id.id,
                        'send_qty':stock_available_qty,
                        'send_as':line[4],
                        'send_as_new':line[4],
                        'source_location':stock_product.location_id.id,
                        'delivery_address':line[2] if line[2] else '',
                        'weight':line[3] if line[2] else '',
                        'location_label':line[6] if line[6] else '',
                        'scan_package_number':line[7] if line[7] else '',
                        })]})

        if len(product_list)>0:
            self.wo_id.message_post(body=_('<div>Below List Of product Not found in system related to merchant please review </div><div> '+str(product_list) +'</div>'))

        if len(stock_not_list)>0:
            self.wo_id.message_post(body=_('<div>Below List Of Product Not having requested stock please review </div><div> '+str(stock_not_list) +'</div>'))

                



        

    def bulk_import(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file)) # self.xls_file is your binary field
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        print(sheet.nrows)
        product_list=[]
        location_list=[]
        for row_no in range(sheet.nrows):
            if row_no <= 0:
                fields = map(lambda row:row.value.encode('utf-8'), sheet.row(row_no))
            else:
                line = list(map(
                                lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                    row.value), sheet.row(row_no)))
                # in above line variable,
                if line[0]:
                    product_id = self.env['product.product'].search([('default_code','=',line[0]),('partner_id','=',self.wro_id.merchand_id.id)],limit=1)
                    location_id = self.env['stock.location'].search([('location_scan_name','=',line[6]),('location_full','!=',True)], limit=1)
                    if product_id:
                        if location_id or not line[6]:
                            if self.wro_id.shipping_type == 'parcel':
                                data={
                                'product_id':product_id.id,
                                'product_qty':int(float(line[1])),
                                'qty_per_box':int(float(line[2])),
                                'no_of_boxes':int(float(line[3])),
                                'package_value':float(line[4]) if line[4] else '',
                                'consolidated_type':line[5],
                                'is_default_location':True if location_id.id else False,
                                'defaultlocation_id':location_id.id if location_id else False

                                }

                                self.wro_id.write({'wro_single_sku_per_box_ids':[(0,0,data)]})
                            else:
                                data={
                                'product_id':product_id.id,
                                'product_qty':int(float(line[1])),
                                'qty_per_pallet':int(float(line[2])),
                                'no_of_pallets':int(float(line[3])),
                                'package_value':float(line[4]) if line[4] else '',
                                'consolidated_type':line[5],
                                'is_default_location':True if location_id.id else False,
                                'defaultlocation_id':location_id.id if location_id else False

                                }
                                self.wro_id.write({'wro_single_sku_per_pallet_ids':[(0,0,data)]})
                        else:
                            location_list.append(line[6])
                    else:
                        product_list.append(line[0])
        if len(product_list)>0:
            self.wro_id.message_post(body=_('<div>Below List Of product Not found in system related to merchant please review </div><div> '+str(product_list) +'</div>'))

        if len(location_list)>0:
            self.wro_id.message_post(body=_('<div>Below List Of Location Not found in system related to merchant please review </div><div> '+str(location_list) +'</div>'))

                

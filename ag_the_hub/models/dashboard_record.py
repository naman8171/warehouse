# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import date, timedelta
from odoo.tools import groupby as groupbyelem
from operator import attrgetter, itemgetter


class DashboardDynamics(models.Model):
    _name = "dashboard.dynamics"


    merchand_id = fields.Many2one("res.partner",string="Merchant",domain="[('contact_type','=','Merchant')]")
    total_products = fields.Float("Total Products")
    stock_one_hand = fields.Float("Stock on Hand")
    low_stock_product = fields.Float("Low Stock Product")
    out_stock_product = fields.Float("Out Stock Product")
    top_stock_product = fields.Float("Top Stock Product")
    inventory_value = fields.Float("Inventory Value")
    reorder_alert = fields.Float("Reorder Alert")
    most_recent_wo = fields.Float("Most Recent WO")
    most_recent_wro = fields.Float("Most Recent WRO")
    recent_wo_status = fields.Float("Recent WO status")
    current_month_total_qty = fields.Float()



    def update_merchant_dashboard(self):
        Workorders = self.env['thehub.workorder'].sudo()
        wro_env = self.env['warehouse.receive.order'].sudo()
        Products = self.env['product.template'].sudo()
        inventory_env = self.env['stock.quant'].sudo()
        wo_line = self.env['thehub.workorder.lines'].sudo()
        user_id = self.env['res.users'].sudo()
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        last_ten_days_date=fields.Datetime.now()- timedelta(days=10)
        # last_ten_days_day=last_ten_days_date.day
        # last_ten_days_month=last_ten_days_date.month
        month = fields.Date.today().strftime("%B, %Y")
        
        
        merchand_ids=self.env['res.partner'].sudo().search([('contact_type','=','Merchant')])
        for merchand_id in merchand_ids:
            user_id = user_id.search([('partner_id','=',merchand_id.id)])
            if user_id:
                domain_product = [('responsible_id', '=', user_id.id)]
                cm_products_count = len(Products.search(domain_product))
                products_count = Products.search_count(domain_product)
                domain=[('owner_id', '=', merchand_id.id),('quantity','>',0),('location_id.usage','=','internal'),('product_id.active','=',True)]
                inventory_record = inventory_env.search(domain)
                inventory_ids_list =[]
                product_id=[]
                total_qty=0
                current_month_total_qty=0
                low_stock_product_list=[]
                zero_stock_product_list=[]
                count=0
                productcount_list=[]
                low_stock_product=0
                zero_stock_product=0
                top_selling_product=0
                for quant in inventory_record:
                    
                    if quant.product_id.responsible_id.id == user_id.id:
                        if quant.create_date.month == current_month and quant.create_date.year == current_year:
                            quantity=quant.quantity #- quant.reserved_quantity
                            current_month_total_qty+=quantity
                        if quant.product_id.id not in  productcount_list:
                            wo_line_len = len(wo_line.search([('product_id','=',quant.product_id.id),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year).ids)
                            if wo_line_len>0:
                                top_selling_product+=1
                        quantity=quant.quantity #- quant.reserved_quantity
                        total_qty+=quantity
                        if quantity>0 and quant.product_id.id not in product_id:
                            inventory_ids_list.append(quant.id)
                            product_id.append(quant.product_id.id)
                        if quantity<=quant.product_id.reorder_level and quant.product_id.id not in low_stock_product_list:
                            low_stock_product+=1
                            low_stock_product_list.append(quant.product_id.id)
                        if quantity <=0 and quant.product_id.id not in zero_stock_product_list:
                            zero_stock_product+=1
                            
                            zero_stock_product_list.append(quant.product_id.id)
                        productcount_list.append(quant.product_id.id)

                domain=[('responsible_id', '=', user_id.id)]
                product_ids=self.env['product.product'].sudo().search(domain)
                productcount_list+=product_ids.ids
                wo_line_len = len(wo_line.search([('product_id','in',productcount_list),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year).ids)
                for product in product_ids:
                    if product.qty_available<=product.reorder_level:
                        low_stock_product+=1
                    if product.qty_available<=0:
                        zero_stock_product+=1

                domain = [('merchand_id', '=', merchand_id.id)]
                ten_wo_ids=Workorders.search(domain).filtered(lambda x: x.create_date >= last_ten_days_date)
                
                ten_wro_ids = wro_env.search(domain).filtered(lambda x: x.create_date >= last_ten_days_date)
                wo_returned_count = Workorders.search_count(domain + [('status', '=', 'Returned')])
                group_by_fields=['product_id']
                record_data = wo_line.sudo().search([('product_id','in',product_ids.ids),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year)
                grouped_data = [wo_line.sudo().concat(*g) for k, g in groupbyelem(record_data, itemgetter('product_id'))]
                vals={
                'total_products':cm_products_count,
                'stock_one_hand':total_qty,
                'low_stock_product':low_stock_product,
                'out_stock_product':zero_stock_product,
                'top_stock_product':len(grouped_data),
                'inventory_value':products_count,
                'most_recent_wo':len(ten_wo_ids.ids),
                'most_recent_wro':len(ten_wro_ids.ids),
                'recent_wo_status': wo_returned_count,
                'merchand_id':merchand_id.id,
                'current_month_total_qty':current_month_total_qty
                }
                dashboard_id=self.sudo().search([('merchand_id','=',merchand_id.id)])
                if dashboard_id:
                    dashboard_id.write(vals)
                else:
                    dashboard_id.create(vals)

        


    def update_specific_merchant_dashboard(self):
        Workorders = self.env['thehub.workorder'].sudo()
        wro_env = self.env['warehouse.receive.order'].sudo()
        Products = self.env['product.template'].sudo()
        inventory_env = self.env['stock.quant'].sudo()
        wo_line = self.env['thehub.workorder.lines'].sudo()
        user_id = self.env['res.users'].sudo()
        current_month = fields.Date.today().month
        current_year = fields.Date.today().year
        last_ten_days_date=fields.Datetime.now()- timedelta(days=10)
        # last_ten_days_day=last_ten_days_date.day
        # last_ten_days_month=last_ten_days_date.month
        month = fields.Date.today().strftime("%B, %Y")
        
        for merchand_id in self.merchand_id:
            user_id = user_id.search([('partner_id','=',merchand_id.id)])
            if user_id:
                domain_product = [('responsible_id', '=', user_id.id)]
                cm_products_count = len(Products.search(domain_product))
                products_count = Products.search_count(domain_product)
                domain=[('owner_id', '=', merchand_id.id),('quantity','>',0),('location_id.usage','=','internal'),('product_id.active','=',True)]
                inventory_record = inventory_env.search(domain)
                inventory_ids_list =[]
                product_id=[]
                total_qty=0
                current_month_total_qty=0
                low_stock_product_list=[]
                zero_stock_product_list=[]
                count=0
                productcount_list=[]
                low_stock_product=0
                zero_stock_product=0
                top_selling_product=0
                for quant in inventory_record:
                    
                    if quant.product_id.responsible_id.id == user_id.id:
                        if quant.create_date.month == current_month and quant.create_date.year == current_year:
                            quantity=quant.quantity# - quant.reserved_quantity
                            current_month_total_qty+=quantity
                        if quant.product_id.id not in  productcount_list:
                            wo_line_len = len(wo_line.search([('product_id','=',quant.product_id.id),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year).ids)
                            if wo_line_len>0:
                                top_selling_product+=1
                        quantity=quant.quantity #- quant.reserved_quantity
                        total_qty+=quantity
                        if quantity>0 and quant.product_id.id not in product_id:
                            inventory_ids_list.append(quant.id)
                            product_id.append(quant.product_id.id)
                        if quantity<=quant.product_id.reorder_level and quant.product_id.id not in low_stock_product_list:
                            low_stock_product+=1
                            low_stock_product_list.append(quant.product_id.id)
                        if quantity <=0 and quant.product_id.id not in zero_stock_product_list:
                            zero_stock_product+=1
                            
                            zero_stock_product_list.append(quant.product_id.id)
                        productcount_list.append(quant.product_id.id)

                domain=[('responsible_id', '=', user_id.id),('id','not in',productcount_list)]
                product_ids=self.env['product.product'].sudo().search(domain)
                productcount_list+=product_ids.ids
                wo_line_len = len(wo_line.search([('product_id','in',productcount_list),('workorder_id','!=',False)]).filtered(lambda x: x.create_date.month == current_month and x.create_date.year == current_year).ids)
                for product in product_ids:
                    if product.qty_available<=product.reorder_level:
                        low_stock_product+=1
                    if product.qty_available<=0:
                        zero_stock_product+=1

                domain = [('merchand_id', '=', merchand_id.id)]
                ten_wo_ids=Workorders.search(domain).filtered(lambda x: x.create_date >= last_ten_days_date)
                
                ten_wro_ids = wro_env.search(domain).filtered(lambda x: x.create_date >= last_ten_days_date)
                wo_returned_count = Workorders.search_count(domain + [('status', '=', 'Returned')])
                stock_one_hand = sum(inventory_record.mapped('quantity'))
                vals={
                'total_products':cm_products_count,
                'stock_one_hand': stock_one_hand, # total_qty,
                'low_stock_product':low_stock_product,
                'out_stock_product':zero_stock_product,
                'top_stock_product':top_selling_product,
                'inventory_value':products_count,
                'most_recent_wo':len(ten_wo_ids.ids),
                'most_recent_wro':len(ten_wro_ids.ids),
                'recent_wo_status': wo_returned_count,
                'merchand_id':merchand_id.id,
                'current_month_total_qty':current_month_total_qty
                }
                
                self.write(vals)
                
        

    

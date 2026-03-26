
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime

class UpdateQuantity(models.Model):
    _name = "wizard.update.quantity"
    _description = "Update Quantity"



    product_qty = fields.Float("Shipment Quantity")
    qty_per_box = fields.Float("Quantity/Box")
    no_of_boxes = fields.Float("#Of Boxes")
    package_value = fields.Float("Package Value")
    product_per_box_id = fields.Many2one('wro.single.sku.per.box',string="product per box")
    product_per_pallet_id = fields.Many2one('wro.single.sku.per.pallet',string="product per pallet")
    product_per_box_line_id = fields.Many2one('single.sku.per.box.line',string="product per box")
    product_per_product_line_id = fields.Many2one('single.sku.per.box.product.line',string="product per pallet")
    box_size = fields.Many2one('box.size', string="Type of Box")
    is_package = fields.Boolean('Is Package')
    packing_categ = fields.Selection([('Carton Sizes', 'Carton Sizes'),
                                    ('Flyer Size', 'Flyer Size'),
                                    ('Pallet', 'Pallet')], string="Packing category")
    packing_type_id = fields.Many2one('thehub.packing.type',domain="[('packing_categ', '=', packing_categ),('packing_type','=','wro')]")


    file = fields.Binary()
    filename = fields.Char()
    
    
    @api.model
    def default_get(self, fields):
        res = super(UpdateQuantity, self).default_get(fields)
        if 'product_per_box_id' in res:
            product_per_box_id=self.env['wro.single.sku.per.box'].sudo().browse(res['product_per_box_id'])
            res['product_qty']=product_per_box_id.product_qty
            res['qty_per_box']=product_per_box_id.qty_per_box
            res['no_of_boxes']=product_per_box_id.no_of_boxes
            res['package_value']=product_per_box_id.package_value
            res['box_size']=product_per_box_id.box_size.id
        elif 'product_per_pallet_id' in res:
            product_per_pallet_id=self.env['wro.single.sku.per.pallet'].sudo().browse(res['product_per_pallet_id'])
            res['product_qty']=product_per_pallet_id.product_qty
            res['qty_per_box']=product_per_pallet_id.qty_per_pallet
            res['no_of_boxes']=product_per_pallet_id.no_of_pallets
            res['package_value']=product_per_pallet_id.package_value

        
        return res

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if self.product_qty:
            self.qty_per_box=self.product_qty
            self.no_of_boxes=1


    @api.onchange('qty_per_box')
    def _onchange_qty_per_box(self):
        if self.product_qty:
            self.no_of_boxes=self.product_qty/self.qty_per_box
    

    @api.onchange('no_of_boxes')
    def _onchange_no_of_boxes(self):
        if self.product_qty:
            self.qty_per_box=self.product_qty/self.no_of_boxes
    
    
    def update_packing(self):
        if self.product_per_box_line_id:
            self.product_per_box_line_id.write({
                'is_package_required':True,
                'packing_type_id':self.packing_type_id,
                
                })
            body = _("<strong>Add Packaging: </strong><div><div>Packing Type :- %s</div><div>Packing :- %s </div></div>"%(self.packing_categ,self.packing_type_id.name))
                

            self.product_per_box_line_id.wro_single_sku_per_box_id.wro_id.message_post(body=body)
            #print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",self.product_per_box_line_id.wro_single_sku_per_box_id.wro_id,self.product_per_box_line_id.wro_single_sku_per_box_id)
            return {'type': 'ir.actions.act_window',
                'res_model': 'wro.single.sku.per.box',
                'view_mode': 'form',
                'target': 'new',
                'res_id':self.product_per_box_line_id.wro_single_sku_per_box_id.id,
                }
        elif self.product_per_product_line_id:
            if self.product_per_product_line_id.wro_single_sku_per_box_line_id:
                self.product_per_product_line_id.write({
                    'is_package_required':True,
                    'packing_type_id':self.packing_type_id,
                    
                    })
                body = _("<strong>Add Packaging: </strong><div><div>Packing Type :- %s</div><div>Packing :- %s </div></div>"%(self.packing_categ,self.packing_type_id.name))
                    

                self.product_per_product_line_id.wro_single_sku_per_box_line_id.wro_single_sku_per_box_id.wro_id.message_post(body=body)
                #print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",self.product_per_box_line_id.wro_single_sku_per_box_id.wro_id,self.product_per_box_line_id.wro_single_sku_per_box_id)
                return {'type': 'ir.actions.act_window',
                    'res_model': 'single.sku.per.box.line',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_id':self.product_per_product_line_id.wro_single_sku_per_box_line_id.id,
                    }
            elif self.product_per_product_line_id.wro_single_sku_per_pallet_line_id:
                self.product_per_product_line_id.write({
                    'is_package_required':True,
                    'packing_type_id':self.packing_type_id,
                    
                    })
                body = _("<strong>Add Packaging: </strong><div><div>Packing Type :- %s</div><div>Packing :- %s </div></div>"%(self.packing_categ,self.packing_type_id.name))
                    

                self.product_per_product_line_id.wro_single_sku_per_pallet_line_id.wro_single_sku_per_pallet_id.wro_id.message_post(body=body)
                #print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",self.product_per_box_line_id.wro_single_sku_per_box_id.wro_id,self.product_per_box_line_id.wro_single_sku_per_box_id)
                return {'type': 'ir.actions.act_window',
                    'res_model': 'single.sku.per.box.line',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_id':self.product_per_product_line_id.wro_single_sku_per_pallet_line_id.id,
                    }





            



    def update_quantity(self):
        content=''
        count=False
        if self.product_per_box_id:
            if self.product_per_box_id.product_qty != self.product_qty:
                content+="<div>Product QTY :"+str(self.product_qty)+"</div>"
                count=True
            if self.product_per_box_id.qty_per_box != self.qty_per_box:
                content+="<div>Qty per box :"+str(self.qty_per_box)+"</div>"
                count=True
            if self.product_per_box_id.no_of_boxes != self.no_of_boxes:
                content+="<div>No Of Boxes :"+str(self.no_of_boxes)+"</div>"
                count=True
            if self.product_per_box_id.package_value != self.package_value:
                content+="<div>Package Value :"+str(self.package_value)+"</div>"
                count=True
            if self.product_per_box_id.box_size.name != self.box_size.name:
                content+="<div>Box Size :"+str(self.box_size.name)+"</div>"
                count=True
            if count:
                body = _("<strong>Update Location: </strong><div>%s</div>",content)
                

                self.product_per_box_id.wro_id.message_post(body=body)

            
            self.product_per_box_id.write({
                'product_qty':self.product_qty,
                'qty_per_box':self.qty_per_box,
                'no_of_boxes':self.no_of_boxes,
                'package_value':self.package_value,
                'box_size':self.box_size.id
                })


            for rec in self.product_per_box_id:
                consolidated_type=rec.consolidated_type
                wro_single_sku_per_box_id = rec
                if wro_single_sku_per_box_id:
                    wro_single_sku_per_box_id.update({
                            'qty_per_box': self.qty_per_box,
                            'no_of_boxes': self.no_of_boxes,
                            'box_size': self.box_size.id,
                            'wro_single_sku_per_box_line_ids':[(6,0,[])]
                        })
                iteration_time = 0
                box_line_count = self.env['single.sku.per.box.line'].sudo().search_count([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)])
                if not box_line_count:
                    iteration_time = int(wro_single_sku_per_box_id.no_of_boxes)
                elif box_line_count < wro_single_sku_per_box_id.no_of_boxes:
                    iteration_time = wro_single_sku_per_box_id.no_of_boxes - box_line_count
                elif box_line_count > wro_single_sku_per_box_id.no_of_boxes:
                    iteration_time = box_line_count - wro_single_sku_per_box_id.no_of_boxes
                    self.env['single.sku.per.box.line'].sudo().search([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)], limit=iteration_time, order='package_number desc').unlink()
                    iteration_time = 0
                iteration_time=self.no_of_boxes

                for i in range(0, int(iteration_time)):
                    # self.env['single.sku.per.box.line'].sudo().search([('wro_single_sku_per_box_id', '=', wro_single_sku_per_box_id.id)]).unlink()
                    box_line_id = self.env['single.sku.per.box.line'].sudo().create({
                            'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.box.line'),
                            'wro_single_sku_per_box_id': wro_single_sku_per_box_id.id,
                            'send_as':consolidated_type
                        })
                    if consolidated_type=='non_consolidated':
                        for j in range(0,int(rec['qty_per_box'])):
                            box_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                'package_number': box_line_id.package_number+'/'+str(j+1),
                                'wro_single_sku_per_box_line_id': box_line_id.id,
                                
                            })
                            #print("nnnnnnnnnnnnnnnnnnnn",box_product_line_id)

        else:
            if self.product_per_pallet_id.product_qty != self.product_qty:
                content+="<div>Product QTY :"+str(self.product_qty)+"</div>"
                count=True
            if self.product_per_pallet_id.qty_per_pallet != self.qty_per_box:
                content+="<div>Qty per box :"+str(self.qty_per_box)+"</div>"
                count=True
            if self.product_per_pallet_id.no_of_pallets != self.no_of_boxes:
                content+="<div>No Of Boxes :"+str(self.no_of_boxes)+"</div>"
                count=True
            if self.product_per_pallet_id.package_value != self.package_value:
                content+="<div>Package Value :"+str(self.package_value)+"</div>"
                count=True
            if count:
                body = _("<strong>Update Location: </strong><div>%s</div>",content)
                

                self.product_per_pallet_id.wro_id.message_post(body=body)
            
            self.product_per_pallet_id.write({
                'product_qty':self.product_qty,
                'qty_per_pallet':self.qty_per_box,
                'no_of_pallets':self.no_of_boxes,
                'package_value':self.package_value,
                })

            for rec in self.product_per_pallet_id:
                consolidated_type=rec.consolidated_type
                wro_single_sku_per_pallet_id = rec
                if wro_single_sku_per_pallet_id:
                    wro_single_sku_per_pallet_id.update({
                            'qty_per_pallet': self.qty_per_box,
                            'no_of_pallets': self.no_of_boxes,
                            'wro_single_sku_per_pallet_line_ids':[(6,0,[])]
                        })
                iteration_time = 0
                pallet_line_count = self.env['single.sku.per.pallet.line'].sudo().search_count([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)])
                if not pallet_line_count:
                    iteration_time = int(wro_single_sku_per_pallet_id.no_of_pallets)
                elif pallet_line_count < wro_single_sku_per_pallet_id.no_of_pallets:
                    iteration_time = wro_single_sku_per_pallet_id.no_of_pallets - pallet_line_count
                elif pallet_line_count > wro_single_sku_per_pallet_id.no_of_pallets:
                    iteration_time = pallet_line_count - wro_single_sku_per_pallet_id.no_of_pallets
                    self.env['single.sku.per.pallet.line'].sudo().search([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)], limit=iteration_time, order='package_number desc').unlink()
                    iteration_time = 0
                iteration_time=self.no_of_boxes
                for i in range(0, int(iteration_time)):
                    # self.env['single.sku.per.pallet.line'].sudo().search([('wro_single_sku_per_pallet_id', '=', wro_single_sku_per_pallet_id.id)]).unlink()
                    pallet_line_id=self.env['single.sku.per.pallet.line'].sudo().create({
                            'package_number': self.env['ir.sequence'].sudo().next_by_code('single.sku.per.pallet.line'),
                            'wro_single_sku_per_pallet_id': wro_single_sku_per_pallet_id.id,
                            'send_as':consolidated_type
                        })
                    if consolidated_type=='non_consolidated':
                        for j in range(0,int(rec.qty_per_pallet)):
                            pallet_product_line_id = self.env['single.sku.per.box.product.line'].sudo().create({
                                'package_number': pallet_line_id.package_number+'/'+str(j+1),
                                'wro_single_sku_per_pallet_line_id': pallet_line_id.id,
                                
                            })




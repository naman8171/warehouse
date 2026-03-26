
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, time, datetime

class ScannedpackageNumber(models.TransientModel):
    _name = "scanned.package.number"
    

    wo_id = fields.Many2one('thehub.workorder')
    scan_location = fields.Char('Scan location Name')
    is_packages = fields.Boolean()



    def update_package_name(self):
        if self.is_packages:
            count=0
            for line in self.wo_id.package_lines:
                if line.name == self.scan_location:
                    line.scan_package_number=self.scan_location
                    count=1
            if count==0:
                raise UserError(_("Package not available inside lines"))
        else:
            count=0
            for line in self.wo_id.wo_line_ids:
                if line.package_id.name == self.scan_location:
                    line.scan_package_number=self.scan_location
                    line.scanned_qty+=1
                    count=1
            if count==0:
                raise UserError(_("Package not available inside lines"))


    def update_package_again_name(self):
        if self.is_packages:
            count=0
            for line in self.wo_id.package_lines:
                if line.name == self.scan_location:
                    line.scan_package_number=self.scan_location
                    count=1
            if count==0:
                raise UserError(_("Package not available inside lines"))
            else:
                return {'type': 'ir.actions.act_window',
                        'res_model': 'scanned.package.number',
                        'view_mode': 'form',
                        'target': 'new',
                        'context':{'default_wo_id':self.wo_id.id,'default_is_packages':True}
                        }

        else:
            count=0
            for line in self.wo_id.wo_line_ids:
                if line.package_id.name == self.scan_location:
                    line.scan_package_number=self.scan_location
                    count=1
            if count==0:
                raise UserError(_("Package not available inside lines"))
            else:
                return {'type': 'ir.actions.act_window',
                    'res_model': 'scanned.package.number',
                    'view_mode': 'form',
                    'target': 'new',
                    'context':{'default_wo_id':self.wo_id.id}
                    }



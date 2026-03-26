odoo.define('ag_the_hub.product_search', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
publicWidget.registry.PortalProductSearch = publicWidget.Widget.extend({

    selector: '.o_products_search_index',
    events: {
        'click .line_record_delete': '_onTagRemove',
        'change .o_product_tags_form select': '_onTagAdd',
        'click #warehouse_submit': '_onSubmitWarehouse',
        'click #products_submit': '_onSubmitProducts',
        'click #shipping_type_submit': '_onSubmitShippingType',
        'change #productFragileCheckbox' : '_onChangeProductFragileCheckbox',
        'change #warehouse': '_onChangeWarehouse',
        'click #shipment_qty_submit': '_onSubmitQtyShipment',
        'change #arrival_date': '_onChangeArrivalDate',
        'click #arrival_date_submit': '_onSubmitArrivalDate',
        'change .pickup_method': '_onChangePickupMethod',
        'click #wro_submit': "_onSubmitWro"
    },

    start: function () {
        const wroId = $('#wroId').val();
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'get_saved_product',
            args: [[], [wroId]],
        }).then(function (result) {
            for(var i=0;i<result.length;i++){
                var select = $(".ms-options").find('li input[value="' + result[i].product_id + '"]');
                select.trigger('click');
            }
        });
        return this._super.apply(this, arguments);
    },


    _onSubmitWarehouse : function (ev) {
        ev.preventDefault();
        const wroId = $('#wroId').val();

        const warehouse = $('#warehouse').val();
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_submit_warehouse',
            args: [[], [warehouse], [wroId]],
        }).then(function (result) {
            const url = window.location.pathname + '/' + result.toString();
            $('#collapseOne').removeClass('show');
            $('#collapseTwo').addClass('show');
            $('#warehouse_edit_btn').removeClass('disabled');
            location.replace(url);
        });
    },

    _onSubmitWro : function (ev) {
        ev.preventDefault();
        const wroId = $('#wroId').val();
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_wro_submit',
            args: [[], [wroId]],
        }).then(function (result) {
            const url = window.location.origin + '/my/wros';
            location.replace(url);
        });
    },


    _onChangeWarehouse : function (ev) {
        ev.preventDefault();
        const warehouse = $('#warehouse').val();
        if (warehouse){
            $('#warehouse_submit').removeClass('disabled');
        }
        else{
            $('#warehouse_submit').addClass('disabled');
        }
    },

    _onChangeProductFragileCheckbox : function (ev) {
        ev.preventDefault();
        const products_fragile = $('#productFragileCheckbox');
        if ($('#productFragileCheckbox')[0].checked){
            $('#products_submit').removeClass('disabled');
        }
        else{
            $('#products_submit').addClass('disabled');
        }
    },

    _onTagAdd: function () {
        let self = this;
        var product_ids = $("#select_multi_product").val();
        self._rpc({
            model: 'product.product',
            method: 'get_product_data',
            args: [[], [product_ids]],
        }).then(function (result) {
            if(result.length > 0){
                $("#productTableDiv").removeClass('d-none');
                var tr_IDs = [];
                var result_tr_IDs = []
                $("#productTable tbody").find("tr").each(function(){ tr_IDs.push(this.id); });
                var html_content = "";
                for(var i=0;i<result.length;i++){
                    if(result_tr_IDs.indexOf("product_id_" + result[i].id) == -1){
                        result_tr_IDs.push("product_id_" + result[i].id);
                    }
                    if(result[i].platform == false){
                        var platform = ''
                    }
                    else{
                        var platform = result[i].platform
                    }
                    if($("#product_id_" + result[i].id).length == 0){
                        html_content += '<tr id="product_id_' + result[i].id + '">\
                                <td>' + result[i].name + '</td>\
                                <td>' + result[i].default_code + '</td>\
                                <td>' + platform + '</td>\
                                <td><input type="number" min="1" class="form-control" id="product_qty_' + result[i].id + '" name="product_qty_' + result[i].id + '" value="1"/></td>\
                                <td><input type="number" min="1" class="form-control" id="package_value_' + result[i].id + '" name="package_value_' + result[i].id + '" value="0" onchange="setTwoNumberDecimal(this)"/></td>\
                                <td width="50px">\
                                    <button id="delete_record_' + result[i].id + '" type="button" class="btn btn-link line_record_delete" style="font-size:18px;color:black;" name="delete"><i class="fa fa-trash-o"/></button>\
                                </td>\
                        </tr>'
                    }
                }
                for(var i=0;i<tr_IDs.length;i++){
                    if(result_tr_IDs.indexOf(tr_IDs[i]) == -1){
                        $("#" + tr_IDs[i]).remove();
                    }
                }
                $("#productTable tbody").append(html_content);
                const wroId = $('#wroId').val();
                self._rpc({
                    model: 'warehouse.receive.order',
                    method: 'get_saved_product',
                    args: [[], [wroId]],
                }).then(function (output) {
                    for(var i=0;i<output.length;i++){
                        if($("#product_qty_" + output[i].product_id).length > 0){
                            $("#product_qty_" + output[i].product_id)[0].value = output[i].product_qty;
                        }
                    }
                });
            }
            else{
                $("#productTableDiv").addClass('d-none');
            }
        });
    },

    _onTagRemove: function (event) {
        const product_id = $(event)[0].currentTarget.id.split('_');
        var select = $(".ms-options").find('li.selected input[value="' + product_id[product_id.length-1] + '"]');
        select.trigger('click');
    },

    _onSubmitProducts : function (ev) {
        ev.preventDefault();
        let product_ids = $("#select_multi_product").val();
        let data = []
        const wroId = $('#wroId').val();
        for(var i=0;i<product_ids.length;i++){
            var vals = {
                'product_id': parseInt(product_ids[i]),
                'product_qty': parseInt($("#product_qty_" + product_ids[i]).val()),
                'package_value': parseInt($("#package_value_" + product_ids[i]).val()),
            }
            data.push(vals);
        }
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_update_wro_lines',
            args: [[], [data], [wroId], [product_ids]],
        }).then(function(output) {
            $('#collapseTwo').removeClass('show');
            $('#collapseThree').addClass('show');
            $('#search_product_edit_btn').removeClass('disabled');
        });
    },

    _onSubmitShippingType : function (ev) {
        ev.preventDefault();
        let self = this;
        const wroId = $('#wroId').val();
        var shipping_type;
        var inventory_type;
        if($('#parcel')[0].checked){
            shipping_type = 'parcel';
            if($('#inventory_type_parcel1')[0].checked){
                inventory_type = 'single';
            }
            else{
                inventory_type = 'multiple';
            }
        }
        else if($('#pallet')[0].checked){
            shipping_type = 'pallet';
            if($('#inventory_type_pallet1')[0].checked){
                inventory_type = 'single';
            }
            else{
                inventory_type = 'multiple';
            }
        }
        else{
            shipping_type = 'container';
            inventory_type = false;
        }
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_update_shipping_type',
            args: [[], [wroId], [shipping_type], [inventory_type]],
        }).then(function(output) {
            location.reload();
        });
    },

    _onSubmitQtyShipment: function(ev){
        ev.preventDefault();
        let self = this;
        let data = []
        const wroId = $('#wroId').val();
        var type_consolated= false;
        try {
            type_consolated=document.querySelector('input[name="consolited_type"]:checked').value;
        }
        catch(err) {
            type_consolated=false
        }
        if($('#parcel')[0].checked){
            if($('#inventory_type_parcel1')[0].checked){
                let single_sku_box_line_ids = JSON.parse($("#single_sku_box_line_ids").val());
                for(var i=0;i<single_sku_box_line_ids.length;i++){
                    var vals = {
                        'line_id': single_sku_box_line_ids[i],
                        'qty_per_box': parseInt($("#single_sku_qty_per_box_" + single_sku_box_line_ids[i]).val()),
                        'no_of_boxes': parseInt($("#no_of_box_qty_" + single_sku_box_line_ids[i]).val()),
                        'box_size': $("#box_size_" + single_sku_box_line_ids[i]).val(),
                        'consolidated_type': $("#consolidated_type_" + single_sku_box_line_ids[i]).val(),
                    }
                    data.push(vals);
                }
            }
            else{
            }
        }
        else if($('#pallet')[0].checked){
            if($('#inventory_type_pallet1')[0].checked){
                let single_sku_pallet_line_ids = JSON.parse($("#single_sku_pallet_line_ids").val());
                for(var i=0;i<single_sku_pallet_line_ids.length;i++){
                    var vals = {
                        'line_id': single_sku_pallet_line_ids[i],
                        'qty_per_pallet': parseInt($("#single_sku_qty_per_pallet_" + single_sku_pallet_line_ids[i]).val()),
                        'no_of_pallets': parseInt($("#no_of_pallet_qty_" + single_sku_pallet_line_ids[i]).val()),
                        'consolidated_type': $("#consolidated_type_" + single_sku_pallet_line_ids[i]).val(),
                    }
                    data.push(vals);
                }
            }
            else{
            }
        }
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_update_shipment_qty',
            args: [[], [data], [wroId,type_consolated]],
        }).then(function(output) {
            $('#collapseFour').removeClass('show');
            $('#collapseFive').addClass('show');
            $('#shipment_edit_btn').removeClass('disabled');
            window.location = output;
        });
    },

    _onChangePickupMethod : function (ev) {
        ev.preventDefault();
        const arrival_date = $('#arrival_date').val();
        if($('.pickup_method')[0].checked){
            $('#pickup_method_details').removeClass('d-none');
            $('#pickup_method_the_hub').removeClass('d-none');
            $('#pickup_method_other_courier_company').addClass('d-none');
        }
        if($('.pickup_method')[1].checked){
            $('#pickup_method_details').removeClass('d-none');
            $('#pickup_method_the_hub').addClass('d-none');
            $('#pickup_method_other_courier_company').removeClass('d-none');
        }
    },

    _onChangeArrivalDate : function (ev) {
        ev.preventDefault();
        const arrival_date = $('#arrival_date').val();
        if (arrival_date){
            $('#arrival_date_submit').removeClass('disabled');
        }
        else{
            $('#arrival_date_submit').addClass('disabled');
        }
    },

    _onSubmitArrivalDate : function (ev) {
        ev.preventDefault();
        var vals = {}
        const wroId = $('#wroId').val();
        vals['pickup_method'] = $('.pickup_method:checked').val();
        vals['contact_name'] = $('#contact_name').val();
        vals['contact_address'] = $('#contact_address').val();
        vals['contact_email'] = $('#contact_email').val();
        vals['contact_phone'] = $('#contact_phone').val();
        vals['courier_company_name'] = $('#courier_company_name').val();
        vals['tracking_number'] = $('#tracking_number').val();
        vals['arrival_date_th'] = $('#arrival_date_th').val();
        vals['arrival_date_occ'] = $('#arrival_date_occ').val();
        this._rpc({
            model: 'warehouse.receive.order',
            method: 'action_submit_arrival_date',
            args: [[], [vals], [wroId]],
        }).then(function (result) {
            const url = window.location.pathname + '/' + result.toString();
            $('#collapseFive').removeClass('show');
            $('#collapseSix').addClass('show');
            $('#confirm_shipping_edit_btn').removeClass('disabled');
        });
    },
});

return publicWidget.registry.PortalProductSearch;
});



function onchange_quantity_per_box(argument) {
    if(parseFloat(argument.max) < parseFloat(argument.value)){
        argument.value=parseInt(argument.max)
    
    }
    else{
        argument.value=parseInt(argument.value)
    }
    var value =argument.value
    let regexPattern = /^-?[0-9]+$/;
    var classname = argument.name;
    var customkey = $(argument).attr("data-custom_key")
    
    //var content_class = 
    classname=classname.replace('_'+customkey,'')
    var jquery_content = $(argument)
    var box_input = jquery_content.parent().parent()
    if(classname=='single_sku_qty_per_box'){
        var total_qty = argument.max
        var id_package='#no_of_box_qty'+"_"+customkey
        var package_box=box_input.find(id_package)
        var total_package_qty = total_qty/value
        let result = regexPattern.test(total_package_qty);
        console.log("eeeeeeeeeeeeeeeee",result,total_package_qty)
    
        if(result) {
            package_box.val(parseInt(total_package_qty))
        }
        else {
            package_box.val(parseInt(total_qty))
            argument.value=parseInt(1)
            alert("Number of Box, Pallet or Container cannot be in decimal values")
        }
        
    }
    else if(classname=='no_of_box_qty'){

        var id_package='#single_sku_qty_per_box'+"_"+customkey
        var package_box=box_input.find(id_package)
        var total_qty = package_box[0].max
        var total_package_qty = total_qty/value


        let result = regexPattern.test(total_package_qty);
        console.log("eeeeeeeeeeeeeeeee",result,total_package_qty)
    
        if(result) {
            package_box.val(parseInt(total_package_qty))
        }
        else {
            package_box.val(parseInt(total_qty))
            argument.value=parseInt(1)
            alert("Number of Box, Pallet or Container cannot be in decimal values")
        }
        
        
    }

    // body...
}

function onchange_quantity_per_pallet(argument) {
    if(parseFloat(argument.max) < parseFloat(argument.value)){
        argument.value=parseInt(argument.max)
    
    }
    else{
        argument.value=parseInt(argument.value)
    }
    var value =argument.value
    var classname = argument.name;
    var customkey = $(argument).attr("data-custom_key")
    
    //var content_class = 
    classname=classname.replace('_'+customkey,'')
    var jquery_content = $(argument)
    var box_input = jquery_content.parent().parent()
    if(classname=='single_sku_qty_per_pallet'){
        var total_qty = argument.max
        var id_package='#no_of_pallet_qty'+"_"+customkey
        var package_box=box_input.find(id_package)
        var total_package_qty = total_qty/value
        package_box.val(parseInt(total_package_qty))
    }
    else if(classname=='no_of_pallet_qty'){

        var id_package='#single_sku_qty_per_pallet'+"_"+customkey
        var package_box=box_input.find(id_package)
        var total_qty = package_box[0].max
        var total_package_qty = total_qty/value
        package_box.val(parseInt(total_package_qty))
    }
    // body...
}

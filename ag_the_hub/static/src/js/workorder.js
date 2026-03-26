odoo.define('ag_the_hub.workorder', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
var core = require('web.core');
var Qweb = core.qweb;
var ajax = require('web.ajax');
ajax.loadXML('/ag_the_hub/static/src/xml/template.xml', Qweb);


publicWidget.registry.welcome_msg = publicWidget.Widget.extend({
    selector: '#welcome-user',
    events: {
        'click .submit_form': '_onTagRemove',
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onTagRemove: function (env) {
        console.log("22222222222222222222",env.target)
        var user_id = $(env.target).find('.user_env')
        console.log("1111111111111111111",user_id.val())
        ajax.jsonRpc("/update/user", 'call', {'user_id':user_id.val()})
        .then(function(modal){
        })
    }
})


publicWidget.registry.WorkordersLine = publicWidget.Widget.extend({
    selector: '#add_new_workorder',
    events: {
        'click #add_wo_line_ids': '_onClickWorkorderButton',
        'change .o_product_stock_selection select': '_onTagAdd',
        'click .line_record_delete': '_onTagRemove',
        'click .sender_partner':'_onchange_partner_id'
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickWorkorderButton: function () {
        var self = this;
        ajax.jsonRpc("/get/product", 'call', {})
        .then(function(modal){
            var $product_ids = modal.product_ids;
            var $WorkorderLine = $(Qweb.render("WorkOrderLineRows", {'id': ($('.wo_line_row').length + 1), 'product_ids': $product_ids}));
            $('.o_add_an_item_tr').before($WorkorderLine);
            $('#workorder_line_rec').val($('.wo_line_row').length);
            $WorkorderLine.find('.line_workorder_delete span').on('click', function () {
                $(this).parents('tr').remove();
                $('#workorder_line_rec').val($('.wo_line_row').length);
                $('table#productTableWo').find('tr.wo_line_row').each(function (index, element) {
                    var $product = $(element).find('.product select');
                //     var $street = $(element).find('.street input');
                //     var $street2 = $(element).find('.street2 input');
                    var $quantity = $(element).find('.quantity input');
                //     var $state = $(element).find('.state select');
                //     var $country = $(element).find('.country select');
                //     var $zip = $(element).find('.zip input');
                //     var $isCorrespondence = $(element).find('.isCorrespondence input');
                    $product.attr('name', 'product_' + (index + 1))
                //     $street.attr('name', 'street_' + (index + 1))
                //     $street2.attr('name', 'street2_' + (index + 1))
                    $quantity.attr('name', 'quantity_' + (index + 1))
                //     $state.attr('name', 'state_' + (index + 1))
                //     $country.attr('name', 'country_' + (index + 1))
                //     $zip.attr('name', 'zip_' + (index + 1))
                //     $isCorrespondence.attr('name', 'isCorrespondence_' + (index + 1))
                });
            })
        // $WorkorderLine.find('.state_id').on('change', function (ev) {
        //         console.log($(ev).closest('.name'))
        //         alert($(ev.currentTarge).val())
        //     });
        // $WorkorderLine.find('.country_id').on('change', function (ev) {
        //         console.log($(ev).closest('.name'))
        //         alert($(ev.currentTarge).val())
        //     });
        });
    },
    _onchange_partner_id: function (event) {
        var self=this
        if(event.target.value){
            self._rpc({
            model: 'res.partner',
            method: 'get_recipient_address',
            args: [[], parseInt(event.target.value)],
        }).then(function (result) {
            var tr=self.$el.find('#productTableWo tbody tr')
            for(var i=0;i<tr.length;i++){
                var desc = $(tr[i]).find('textarea')
                desc.val(result);
            }

        });
        }
        // body...
    },
    _onTagAdd: function () {
        var product_ids = $("#select_multi_product").val();
        var self=this

        self._rpc({
            model: 'stock.quant',
            method: 'get_product_data',
            args: [[], [product_ids]],
        }).then(function (result) {


            if(result.length > 0){
                var selected_recipient = self.$el.find('.sender_partner')
                if(selected_recipient){
                    self._rpc({
            model: 'res.partner',
            method: 'get_recipient_address',
            args: [[], parseInt(selected_recipient.val())],
        }).then(function (partner_address) {
                            var tr_IDs = [];
                var result_tr_IDs = []
                var html_content = "";
                for(var i=0;i<result.length;i++){
                    $("#productTableWo tbody").html('');
                    if(result_tr_IDs.indexOf("product_id_" + result[i].id) == -1){
                        result_tr_IDs.push("product_id_" + result[i].id);
                    }
                    
                    if($("#product_id_" + result[i].id).length == 0){
                        html_content += '<tr name="product_id_' + result[i].id + '" id="product_id_' + result[i].id + '">\
                                <td><input readonly="readonly" type="text"  class="form-control" name="product_id_' + result[i].id + '" id="product_id_' + result[i].id + '" value="'+result[i].name+'" /></td>\
                                <td>' + result[i].package_number + '</td>\
                                <td>' + result[i].consolidated_type + '</td>\
                                <td>' + result[i].available_quantity + '</td>\
                                <td><input type="number" min="1" max='+result[i].available_quantity+' class="form-control" id="quantity_' + result[i].id + '" name="quantity_' + result[i].id + '" value="1"/></td>\
                                <td><textarea rows="2" cols="50"  class="form-control" id="delivery_address_' + result[i].id + '" name="delivery_address_' + result[i].id + '" value="'+partner_address+'">'+partner_address+'</textarea></td>\
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
                $("#productTableWo tbody").append(html_content);
            // var tr=self.$el.find('#productTableWo tbody tr')
            // console.log("2222222222222222222",tr)
            // for(var i=0;i<tr.length;i++){
            //     var desc = $(tr[i]).find('textarea')
            //     console.log("11111111111111",desc)
            //     desc.val(result);
            // }

        });
                }
                else{
                    var tr_IDs = [];
                var result_tr_IDs = []
                var html_content = "";
                for(var i=0;i<result.length;i++){
                    $("#productTableWo tbody").html('');
                    if(result_tr_IDs.indexOf("product_id_" + result[i].id) == -1){
                        result_tr_IDs.push("product_id_" + result[i].id);
                    }
                    
                    if($("#product_id_" + result[i].id).length == 0){
                        html_content += '<tr name="product_id_' + result[i].id + '" id="product_id_' + result[i].id + '">\
                                <td><input readonly="readonly" type="text"  class="form-control" name="product_id_' + result[i].id + '" id="product_id_' + result[i].id + '" value="'+result[i].name+'" /></td>\
                                <td>' + result[i].package_number + '</td>\
                                <td>' + result[i].consolidated_type + '</td>\
                                <td>' + result[i].available_quantity + '</td>\
                                <td><input type="number" min="1" max='+result[i].available_quantity+' class="form-control" id="quantity_' + result[i].id + '" name="quantity_' + result[i].id + '" value="1"/></td>\
                                <td><textarea rows="2" cols="50"  class="form-control" id="delivery_address_' + result[i].id + '" name="delivery_address_' + result[i].id + '" /></td>\
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
                $("#productTableWo tbody").append(html_content);
                }


                // $("#productTableWo tbody").find("tr").each(function(){ tr_IDs.push(this.id); });


            }
            else{
                $("#productTableWo tbody").html('');
            }
        })
        // body...
    },
    _onTagRemove: function (event) {
        const product_id = $(event)[0].currentTarget.id.split('_');
        var select = $(".ms-options").find('li.selected input[value="' + product_id[product_id.length-1] + '"]');
        select.trigger('click');
    },
    // _onClickAddButton: function () {
    //     var $EmployeeLine = $(Qweb.render("EmployeeRows", {'id': ($('.employee_row').length + 1)}));
    //     $('.o_add_an_employee_tr').before($EmployeeLine);
    //     $('#employee_rec').val($('.employee_row').length);
    //     $EmployeeLine.find('.line_record_delete span').on('click', function () {
    //         $(this).parents('tr').remove();
    //         $('#employee_rec').val($('.employee_row').length);
    //         $('table#employeement_info').find('tr.employee_row').each(function (index, element) {
    //             var $from_date = $(element).find('.from_date input');
    //             var $to_date = $(element).find('.to_date input');
    //             var $position = $(element).find('.position input');
    //             var $organization = $(element).find('.organization input');
    //             var $ref_name = $(element).find('.ref_name input');
    //             var $ref_position = $(element).find('.ref_position input');
    //             var $ref_phone = $(element).find('.ref_phone input');
    //             $from_date.attr('name', 'from_date_' + (index + 1))
    //             $to_date.attr('name', 'to_date_' + (index + 1))
    //             $ref_name.attr('name', 'ref_name_' + (index + 1))
    //             $position.attr('name', 'position_' + (index + 1))
    //             $organization.attr('name', 'organization_' + (index + 1))
    //             $ref_position.attr('name', 'ref_position_' + (index + 1))
    //             $ref_phone.attr('name', 'ref_phone_' + (index + 1))
    //         });
    //     })
    // },
    //  _onClickEducationButton: function () {
    //     var self = this
    //     ajax.jsonRpc("/get/type", 'call', {})
    //     .then(function(modal){
    //         var $line_type_ids = modal.line_type_ids
    //         var $EducationLine = $(Qweb.render("EducationRows", {'id': ($('.education_row').length + 1), 'line_type_ids': $line_type_ids}));
    //         $('.o_add_education_tr').before($EducationLine);
    //         $('#education_rec').val($('.education_row').length);
    //         $EducationLine.find('.education_delete span').on('click', function () {
    //             $(this).parents('tr').remove();
    //             $('#education_rec').val($('.education_row').length);
    //             $('table#education_line_info').find('tr.education_row').each(function (index, element) {
    //                 var $line_type_id = $(element).find('.line_type_id select');
    //                 var $date_start = $(element).find('.date_start input');
    //                 var $date_end = $(element).find('.date_end input');
    //                 var $description = $(element).find('.description input');
    //                 var $name = $(element).find('.name input');
    //                 var $specialization = $(element).find('.specialization input');
    //                 $line_type_id.attr('name', 'line_type_id_' + (index + 1))
    //                 $date_start.attr('name', 'date_start_' + (index + 1))
    //                 $name.attr('name', 'name_' + (index + 1))
    //                 $date_end.attr('name', 'date_end_' + (index + 1))
    //                 $description.attr('name', 'description_' + (index + 1))
    //                 $specialization.attr('name', 'specialization_' + (index + 1))
    //             });
    //         })
    //         // $EducationLine.find('.line_type_id').on('change', function (ev) {
    //         //     console.log($(ev).closest('.name'))
    //         //     alert($(ev.currentTarge).val())
    //         // });
    //     });
    // },
    });
});


function update_view_on_select(argument) {
    if (argument.value == 'My own 3PL Arrangement'){
        var main_content = $('#addWorkorder').find('select[name="multi_pl_company"]').parent().parent()
        main_content.removeClass("d-none");
        //console.log("------------------",main_content)
    }
    else{
        var main_content = $('#addWorkorder').find('select[name="multi_pl_company"]').parent().parent()
        main_content.addClass("d-none");
    }
    // body...
}

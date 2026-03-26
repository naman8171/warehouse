odoo.define('ag_the_hub.wo_status_export', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
var core = require('web.core');
var Qweb = core.qweb;




publicWidget.registry.wo_status_export = publicWidget.Widget.extend({
    selector: '.wo_status',
    events: {
        'click .delete_wo': '_delete_wo',
        'click .file_export': '_export_file',
        'change #select_all': '_select_all'
    },


    _select_all: function (env) {
        console.log("ssssssssssssssssssssssss")
        if(env.target.checked){
            var table=$(this.$el).find('.wo_report')
            // var user_id = $(env.target).find('.user_env')
            var data_tr=table.find('tbody').find('tr')
            for(var i=0;i<data_tr.length;i++){
            var input_checkbox=$(data_tr[i]).find('#wo_status_line')
            if(input_checkbox[0].checked==false){
                input_checkbox.attr("checked", true);
                input_checkbox[0].checked=true
                
                //selected_record.push(parseInt(input_checkbox.val()))
            }
        }

        }
        else{
            var table=$(this.$el).find('.wo_report')
            // var user_id = $(env.target).find('.user_env')
            var data_tr=table.find('tbody').find('tr')
            for(var i=0;i<data_tr.length;i++){
            var input_checkbox=$(data_tr[i]).find('#wo_status_line')
            if(input_checkbox[0].checked){
                input_checkbox.attr("checked", false);
                input_checkbox[0].checked=false
                
                //selected_record.push(parseInt(input_checkbox.val()))
            }
        }
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _export_file: function (env) {
        var table=$(this.$el).find('.wo_report')
        // var user_id = $(env.target).find('.user_env')
        var data_tr=table.find('tbody').find('tr')
        var selected_record=[]
        for(var i=0;i<data_tr.length;i++){
        	var input_checkbox=$(data_tr[i]).find('#wo_status_line')
        	if(input_checkbox[0].checked){
        		selected_record.push(parseInt(input_checkbox.val()))
        	}
        }
        let output = selected_record.some((element) => true);
        if(!output){
        	alert('Please select WO record then export')
            return
        }
        this._rpc({
						model: 'thehub.workorder',
						method: 'export_wo_list',
						args: ['',selected_record],
					}).then(function(output) {
						window.open(output, '_blank');
						// console.log("111111111111111111>>>>>>>>",output)
					})
        // ajax.jsonRpc("/update/user", 'call', {'user_id':user_id.val()})
        // .then(function(modal){
        // })
    },
    _delete_wo: function (env) {
        var table=$(this.$el).find('.wo_report')
        // var user_id = $(env.target).find('.user_env')
        var data_tr=table.find('tbody').find('tr')
        var selected_record=[]
        for(var i=0;i<data_tr.length;i++){
            var input_checkbox=$(data_tr[i]).find('#wo_status_line')
            if(input_checkbox[0].checked){
                selected_record.push(parseInt(input_checkbox.val()))
            }
        }
        let output = selected_record.some((element) => true);
        if(!output){
            alert('Please select WO record then export')
            return
        }
        this._rpc({
                        model: 'thehub.workorder',
                        method: 'delete_wo_list',
                        args: ['',selected_record],
                    }).then(function(output) {
                        location.reload();
                        // console.log("111111111111111111>>>>>>>>",output)
                    })
        // ajax.jsonRpc("/update/user", 'call', {'user_id':user_id.val()})
        // .then(function(modal){
        // })
    }


})


});

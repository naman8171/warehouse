odoo.define('ag_the_hub.inventory_status', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
var core = require('web.core');
var Qweb = core.qweb;


publicWidget.registry.map_data = publicWidget.Widget.extend({
    selector: '#myDiv_wo',
    /**
     * @override
     */
    start: async function () {
        await this._rpc({
            model: 'thehub.workorder',
            method: 'get_graph_data',
            args: [''],
        }).then(function(output) {
            var options = {
                series: [{
                    name: 'Current Month',
                    data: output.list1
                    },
                    {
                    name: 'From Inception',
                    data: output.list2
                    },
                    ],
                    
                    chart: {
                        height: 350,
                        type: 'bar',
                        },
                        plotOptions: {
                        bar: {
                            columnWidth: '45%',
                            distributed: false,
                        }
                        },
                        dataLabels: {
                            enabled: false,
                            
                        },
                        legend: {
                            show: false
                        },
                        stroke: {
                            show: true,
                            width: 2,
                            colors: ['transparent']
                        },
                
                    xaxis: {
                    
                        categories: ['Pending', 'Awaiting', 'Returned', 'Dispatched', 'Delivered', 
                        ],
                        tickPlacement: 'on'
                    },
                    yaxis: {
                    title: {
                        text: 'Servings',
                    },
                    },
                    fill: {
                        opacity: 1,
                        colors: ['#12BF24', '#FF6631'],
                    },
                    tooltip: {
                        y: {
                        formatter: function (val) {
                            return "$ " + val + " thousands"
                        }
                        }
                    }
                    
                };
                
            var chart = new ApexCharts(document.querySelector("#myDiv_wo"), options);
                                                
            chart.render();

        })
        
        // return this._super.apply(this, arguments);
        if (this._super) {
            return this._super.apply(this, arguments);
        } else if (publicWidget.Widget.prototype.start) {
            return publicWidget.Widget.prototype.start.call(this);
        }
    },


});



publicWidget.registry.map_data_wro = publicWidget.Widget.extend({
    selector: '#myDiv_wro_graph',



    /**
     * @override
     */
    start: async function () {
        await this._rpc({
            model: 'warehouse.receive.order',
            method: 'get_graph_data',
            args: [''],
        }).then(function(output) {
            var options = {
                series: [{
                            name: 'Current Month',
                            data: output.list1
                        },
                        {
                            name: 'From Inception',
                            data: output.list2
                        },
                    ],
                    chart: {
                        height: 400,
                        type: 'bar',
                    },
                    plotOptions: {
                        bar: {
                            columnWidth: '45%',
                            distributed: false,
                        }
                    },
                    dataLabels: {
                        enabled: true,
                        position: 'top',
                        
                    },
                    legend: {
                        show: true,
                        position: 'right',
                    },
                    stroke: {
                        show: true,
                        width: 2,
                        colors: ['transparent']
                    },
                
                    xaxis: {
                        categories: ['Submitted', 'Received', 'Stored'],
                        tickPlacement: 'on'
                    },
                    yaxis: {
                        title: {
                            text: 'Warehouse Receiving Order',
                        },
                    },
                    fill: {
                        opacity: 1,
                        colors: ['#12BF24', '#FF6631'],
                    },
                    tooltip: {
                        y: {
                            formatter: function (val) {
                                return  val 
                            }
                        }
                    }
                    
                };
            var chart = new ApexCharts(document.querySelector("#myDiv_wro_graph"), options);                           
            chart.render();
        })
        // console.log("*********", this._super);
        // return this._super.apply(this, arguments);
        // Call the parent class's start method if it exists
        if (this._super) {
            return this._super.apply(this, arguments);
        } else if (publicWidget.Widget.prototype.start) {
            return publicWidget.Widget.prototype.start.call(this);
        }
    },


});




publicWidget.registry.inventory_status_export = publicWidget.Widget.extend({
    selector: '.inventory_status',
    events: {
        'click .file_export': '_export_file',
        'change #select_all': '_select_all'
    },


    _select_all: function (env) {
        if(env.target.checked){
            var table=$(this.$el).find('.inventory_status')
            // var user_id = $(env.target).find('.user_env')
            var data_tr=table.find('tbody').find('tr')
            for(var i=0;i<data_tr.length;i++){
            var input_checkbox=$(data_tr[i]).find('#inventory_status_line')
            if(input_checkbox[0].checked==false){
                input_checkbox.attr("checked", true);
                input_checkbox[0].checked=true
                
                //selected_record.push(parseInt(input_checkbox.val()))
            }
        }

        }
        else{
            var table=$(this.$el).find('.inventory_status')
            // var user_id = $(env.target).find('.user_env')
            var data_tr=table.find('tbody').find('tr')
            for(var i=0;i<data_tr.length;i++){
            var input_checkbox=$(data_tr[i]).find('#inventory_status_line')
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
        // console.log("22222222222222222222",env.target,this)
        var table=$(this.$el).find('.inventory_status')
        // var user_id = $(env.target).find('.user_env')
        // console.log("1111111111111111111",table,)
        var data_tr=table.find('tbody').find('tr')
        var selected_record=[]
        for(var i=0;i<data_tr.length;i++){
        	var input_checkbox=$(data_tr[i]).find('#inventory_status_line')
            // console.log("*****************", $(data_tr[i]).find('#product_name'))
            // var product_name=$(data_tr[i]).find('#product_name').prop("innerText")
            // var product_sku = $(data_tr[i]).find('#product_sku').prop("innerText")
            // var product_barcode=$(data_tr[i]).find('#product_barcode').prop("innerText")
            // var product_qty=$(data_tr[i]).find('#product_qty').prop("innerText")
            // var product_reorder_level=$(data_tr[i]).find('#product_reorder_level').prop("innerText")
            // console.log("9999999999999998888",input_checkbox,
            //     product_name,
            //     product_sku,
            //     product_barcode,
            //     product_qty,
            //     product_reorder_level)
        	if(input_checkbox[0].checked){
        		// console.log("11111111111111111111",input_checkbox[0],input_checkbox.val())
        		selected_record.push(parseInt(input_checkbox.val()))
        	}
        }
        let output = selected_record.some((element) => true);
        // console.log("--------------------------------",selected_record)
        // if(!output){
        // 	alert('Please select Invetory record then export')
        // }
        document.getElementById('custom_loader').style.display = 'block';

        this._rpc({
            model: 'stock.quant',
            method: 'export_inventory_list',
            args: ['', selected_record],
        }).then(function(output) {
            window.open(output, '_blank');
            console.log("Exported File URL >>>>>>>>", output);
        }).catch(function(err) {
            console.error("RPC failed:", err);
            alert("An error occurred while exporting.");
        }).finally(function() {
            // Hide loader
            document.getElementById('custom_loader').style.display = 'none';
        });
    }
})










publicWidget.registry.myDiv_cases = publicWidget.Widget.extend({
    selector: '#myDiv_cases',



    /**
     * @override
     */
    start: async function () {
        console.log("Ddddddddddddddddddddddddd..................................")
        this._rpc({
                        model: 'helpdesk.ticket',
                        method: 'get_portal_info_ticket',
                        args: [''],
                    }).then(function(output) {
                        console.log("333333333333333")
                        var options = {
                                                    series: [{
                                                        name: 'Series 1',
                                                        data: output[0]
                                                    }],
                                                    chart: {
                                                    type: 'bar',
                                                    height: 380
                                                  },
                                                  plotOptions: {
                                                    bar: {
                                                      barHeight: '100%',
                                                      distributed: true,
                                                      
                                                    }
                                                  },
                                                  colors: ['#DFC120', '#E8735E', '#95CBEC', '#45BA45'],
                                                  dataLabels: {
                                                    enabled: true,
                                                    textAnchor: 'start',
                                                    style: {
                                                      colors: ['#fff']
                                                    },
                                                    
                                                    offsetX: 0,
                                                    dropShadow: {
                                                      enabled: true
                                                    }
                                                  },
                                                  legend: {
                                                    horizontalAlign: 'top',
                                                    position: 'right'
                                                  },
                                                  stroke: {
                                                    width: 1,
                                                    colors: ['#fff']
                                                  },
                                                  xaxis: {
                                                    
                                                    categories: ['Open Cases', 'Closed Cases', 'Pending Cases', 'Total Cases'],
                                                    labels: {
                                                        style: {
                                                            colors: '#333',
                                                            fontSize: '12px',
                                                            fontFamily: 'Helvetica, Arial, sans-serif',
                                                        },
                                                    },
                                                  },
                                                  yaxis: {
                                                    labels: {
                                                      show: true
                                                    }
                                                  },
                                                 
                                                  
                                                  tooltip: {
                                                    theme: 'dark',
                                                    x: {
                                                      show: true
                                                    },
                                                    y: {
                                                        formatter: function (val) {
                                                            return "$ " + val + " thousands"
                                                        }
                                                    }
                                                  }
                                                  };
                                                
                                                var chart = new ApexCharts(document.querySelector("#myDiv_cases"), options);
                                                
                                                chart.render();
                    })
        
    //     await this._rpc({
    //                     model: 'warehouse.receive.order',
    //                     method: 'get_graph_data',
    //                     args: [''],
    //                 }).then(function(output) {
    //                     var chart = new CanvasJS.Chart("chartContainer", {
    //     title:{
    //         text: "My First Chart in CanvasJS"              
    //     },
    //     data: [              
    //     {
    //         // Change type to "doughnut", "line", "splineArea", etc.
    //         type: "column",
    //         dataPoints: [
    //             { label: "apple",  y: 10  },
    //             { label: "orange", y: 15  },
    //             { label: "banana", y: 25  },
    //             { label: "mango",  y: 30  },
    //             { label: "grape",  y: 28  }
    //         ]
    //     }
    //     ]
    // });
    // chart.render();
    //                 })
        
        return this._super.apply(this, arguments);
    },


});
});

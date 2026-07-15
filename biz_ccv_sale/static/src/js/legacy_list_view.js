odoo.define('rowno_in_tree.ListNumber', function (require) {
"use strict";

var core = require('web.core');
var ListRenderer = require('web.ListRenderer');
var _t = core._t;
var relational_fields = require('web.relational_fields');
var FieldX2Many = relational_fields.FieldX2Many;
FieldX2Many.include({
    custom_events: _.extend({}, FieldX2Many.prototype.custom_events, {
    	change_stt: '_onchangeSTT'
    }),
    _onchangeSTT: function(ev){
    	ev.stopPropagation();
        var changes = ev.data.changes;
        this._setValue({
            operation: 'UPDATE',
            id: ev.data.dataPointID,
            data: changes,
        })
    }

})

ListRenderer.include({
    _renderRow: function (record) {
    	var self = this;
    	if (this.state.groupedBy.length==0 && this.state.model == 'sale.route.line'){
	    	var index = this.state.data.findIndex(function(e){return record.id===e.id})
	    	if (index!==-1 && (index +1 != record.data.stt)){
	    		record.data.stt = index +1
	    		self.unselectRow().then(function(){
	    			self.trigger_up('change_stt',{
            			dataPointID: record.id,
		    			changes :{sequence: index +1}
		    		})
	    		})
	    	}
    	}
    	var $row = this._super(record);
    	return $row;
    },
    
}); 
});

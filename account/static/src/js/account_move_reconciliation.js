openerp.account = function(instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
instance.web.views.add('form_clone', 'instance.account.extend_form_view');
instance.web.form.tags.add('list_button','instance.account.list_button')
instance.web.form.tags.add('btn_extend','instance.account.btn_extend')
instance.web.form.widgets.add('many2one_pager','instance.account.many2one_pager')
 
instance.account.extend_viewmanager = instance.web.ViewManagerAction.include({
    start : function(){
        this._super()
        if(this.action.context && this.action.context.extended_form_view_id)
            this.setup_exended_form_view(this)
    }, 
    on_mode_switch: function (view_type, no_store, options) {
        self = this
        self.list_loaded = $.when(this._super.apply(this, arguments)).then(function () {
            if(self.action.context && self.action.context.extended_form_view_id)
                self.list_view = self.views['list']
        })
    },
    setup_exended_form_view: function(parent){
        var self = this,
            from_view,
            obj_from_view;
        view_id = this.action.context.extended_form_view_id
        from_view = this.registry.get_object('form_clone');
        this.dataset_form = new instance.web.DataSetSearch(this, 'account.move.reconciliation', this.action.context, this.action.domain);
        this.dataset_loaded  = this.dataset_form.read_slice()
        obj_from_view = new from_view(self, this.dataset_form, view_id, options={});
        obj_from_view.template = 'ExtendedFormView' 
        view_promise = obj_from_view.appendTo(this.$element.find('.oe_extended_form_view'))
        $.when(view_promise, this.dataset_loaded).then(function() {
            if (!_.isEmpty(self.dataset_form.ids)) {
                obj_from_view.on_pager_action('first')
            }
        })
    } 
    
})
instance.account.extend_form_view = instance.web.FormView.extend({
    init :function(){
        this._super.apply(this,arguments);
        this.original_domain = this.getParent().action.domain;
    },
    on_loaded: function(data) {
         this._super.apply(this,arguments);
         var self = this
         this.$element.on('click','a[data-pager-action]',function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });
    },
    do_update_pager: function(hide_index) {
        var index = hide_index ? '-' : this.dataset.index + 1;
        this.$element.find('span.oe_pager_index_extend').html(index).end()
                   .find('span.oe_pager_count_extend').html(this.dataset.ids.length);
    },
    on_pager_action: function(action) {
        var self = this
        var viewmanager = self.getParent();
        viewmanager.action.domain = this.original_domain
        $.when(this._super(action)).then(function() {
            var id = self.get_fields_values().partner_id;
            // apply domain on list
            viewmanager.action.domain = (viewmanager.action.domain || []).concat([["partner_id", "=", id]])
            viewmanager.searchview.do_search()
        })
    },
  })

instance.account.btn_extend = instance.web.form.WidgetButton.extend({
    on_click: function() {
        var self = this;
        this.force_disabled = true;
        this.check_disable();
        this.execute_action().always(function() {
            self.force_disabled = false;
            self.check_disable();
            self.reload_view();
        });
        
    },
    reload_view :function(){
       viewmanager = this.view.getParent().getParent()
       viewmanager.inner_widget.list_view.controller.reload_content();
    },
})

instance.account.list_button = instance.web.form.WidgetButton.extend({
    on_click: function() {
        var self = this
        var list_view = this.view.getParent().list_view.controller
        ids = list_view.get_selected_ids()
        if (ids.length == 0) {
            instance.web.dialog($("<div />").text(_t("You must choose at least one record.")), { title: _t("Warning"), modal: true });
            return false;
        }
        var additional_context = _.extend({
            active_id: ids[0],
            active_ids: ids,
            active_model: list_view.dataset.model
        });
        self.rpc("/web/action/load", {
            action_id: py.eval(this.node.attrs.name),
            context: additional_context
            }, function(result) {
                result.result.context = _.extend(result.result.context || {},
                    additional_context);
                result.result.flags = result.result.flags || {};
                result.result.flags.new_window = true;
                self.do_action(result.result, function () {
                    // reload view
                    list_view.reload();
                    self.getParent().reload()
            });
        });
   }
})
 
}

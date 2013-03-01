openerp.crm = function(openerp) {
    openerp.web_kanban.KanbanRecord.include({
        on_card_clicked: function() {
            if (this.view.dataset.model === 'crm.case.section') {
                this.$('.oe_kanban_crm_salesteams_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
        start: function() {
            this.$(".oe_kanban_crm_salesteams_alias").click(function (event) {
                event.stopPropagation();
                $(this).find("input")[0].select();
            })
            this._super();
        },
    });
};

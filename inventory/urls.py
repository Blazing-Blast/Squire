from django.urls import path, include

from inventory.views import *
from inventory.forms import OwnershipRemovalForm, OwnershipActivationForm

app_name = 'inventory'

urlpatterns = [
    # Change Language helper view
    path('', BoardGameView.as_view(), name='home'),
    path('my_items/', include([
        path('', MemberItemsOverview.as_view(), name='member_items'),
        path('<int:ownership_id>/', include([
            path('take_home/', MemberItemRemovalFormView.as_view(), name='member_take_home'),
            path('give_out/', MemberItemLoanFormView.as_view(), name='member_loan_out'),
            path('edit_note/', MemberOwnershipAlterView.as_view(), name='owner_link_edit'),
        ])),
    ])),
    path('committee/<int:group_id>/', include([
        path('items/', GroupItemsOverview.as_view(), name='committee_items'),
        path('<int:ownership_id>/', include([
            path('edit_note/', GroupItemLinkUpdateView.as_view(), name='owner_link_edit'),
        ])),
    ])),

    path('catalogue/<int:type_id>/', include([
        path('', TypeCatalogue.as_view(), name="catalogue"),
        path('add_new/', CreateItemView.as_view(), name='catalogue_add_new_item'),
        path('<int:item_id>/', include([
            path('update/', UpdateItemView.as_view(), name='catalogue_update_item'),
            path('delete/', DeleteItemView.as_view(), name='catalogue_delete_item'),
            path('links/', include([
                path('', ItemLinkInfoView.as_view(), name='catalogue_item_links'),
                path('<int:link_id>/', include([
                    path('edit/', UpdateLinkView.as_view(), name='catalogue_item_links'),
                    path('activate/', LinkActivationStateView.as_view(
                        form_class=OwnershipActivationForm), name='catalogue_item_link_activation'),
                    path('deactivate/', LinkActivationStateView.as_view(
                        form_class=OwnershipRemovalForm), name='catalogue_item_link_deactivation'),
                    path('delete/', LinkDeletionView.as_view(), name='catalogue_item_link_deletion')
                ])),
            ])),
            path('add_link/', include([
                path('group/', AddLinkCommitteeView.as_view(), name='catalogue_add_group_link'),
                path('member/', AddLinkMemberView.as_view(), name='catalogue_add_member_link')
            ])),

        ])),
    ])),

]

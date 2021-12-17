from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView, FormView, UpdateView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from dynamic_preferences.users.forms import user_preference_form_builder

from core.forms import PasswordChangeForm, AccountForm
from user_interaction.accountcollective import AccountViewMixin


class SiteAccountView(AccountViewMixin, TemplateView):
    template_name = "user_interaction/account_pages/site_account_page.html"


class AccountPasswordChangeView(AccountViewMixin, PasswordChangeView):
    template_name = "user_interaction/account_pages/password_change_form.html"
    success_url = reverse_lazy("account:site_account")
    form_class = PasswordChangeForm

    def form_valid(self, form):
        result = super(AccountPasswordChangeView, self).form_valid(form)
        messages.success(self.request, _("Password succesfully changed"))
        return result


class AccountChangeView(AccountViewMixin, UpdateView):
    template_name = 'user_interaction/account_pages/account_edit.html'
    form_class = AccountForm
    success_url = reverse_lazy('account:site_account')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        message = _("Your account information has been saved successfully!")
        messages.success(self.request, message)
        return super().form_valid(form)


class LayoutPreferencesUpdateView(AccountViewMixin, FormView):
    """ View for updating user preferences """
    template_name = 'user_interaction/preferences_change_form.html'
    success_url = reverse_lazy('account:site_account')

    def get_form_class(self):
        return user_preference_form_builder(instance=self.request.user, section='layout')

    def form_valid(self, form):
        message = _("Your preferences have been updated!")
        messages.success(self.request, message)
        form.update_preferences()
        form = self.get_form()
        return super().form_valid(form)

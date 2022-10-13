from django.http.response import HttpResponse, HttpResponseRedirect
from django.contrib.messages import error as error_msg
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic import ListView, FormView, TemplateView, DetailView
from django.views.generic.edit import CreateView
from django.shortcuts import get_object_or_404

from requests.exceptions import ConnectionError
from easywebdav import OperationFailed

from nextcloud_integration.nextcloud_client import construct_client, OperationFailed
from nextcloud_integration.forms import *
from nextcloud_integration.models import NCFolder, NCFile


__all__ = ["FolderContentView", "FileBrowserView", "FolderCreateView", "SynchFileToFolderView", "DownloadFileview"]


class NextcloudConnectionViewMixin:
    """ Mixin that catches ConnectionErrors from the requests module and throws a 424 (Failed Dependency) instead """
    failed_connection_template = "nextcloud_integration/failed_nextcloud_link.html"
    _client = None

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(NextcloudConnectionViewMixin, self).dispatch(request, *args, **kwargs)
        except ConnectionError as error:
            return self.nextcloud_connection_failed(error)
        except OperationFailed as error:
            return self.nextcloud_operation_failed(error)

    def nextcloud_connection_failed(self, error):
        """ Runs code to handle a fail in the nextcloud connection. Should return a HttpResponse """
        return TemplateResponse(
            self.request,
            self.failed_connection_template,
            context={"error": error},
            status=424 # Failed dependency
        )

    def nextcloud_operation_failed(self, error):
        """ Runs code to handle a fail in the nextcloud connection. Should return a HttpResponse """
        return self.nextcloud_connection_failed(None)

    @property
    def client(self):
        if self._client is None:
            self._client = construct_client()
        return self._client


class FileBrowserView(NextcloudConnectionViewMixin, ListView):
    template_name = "nextcloud_integration/browser.html"
    context_object_name = 'nextcloud_resources'

    def dispatch(self, request, *args, **kwargs):
        try:
            return super(FileBrowserView, self).dispatch(request, *args, **kwargs)
        except OperationFailed as e:
            if e.actual_code == 404:
                return TemplateResponse(
                    request,
                    "nextcloud_integration/browser_not_exist.html",
                    {'folder': kwargs.get('path', '')}
                )


    def get_queryset(self):
        return construct_client().ls(remote_path=self.kwargs.get('path', ''))

class TestFormView(NextcloudConnectionViewMixin, FormView):
    # Todo: Redact
    form_class = FileMoveForm
    template_name = "nextcloud_integration/form.html"

    def get_form_kwargs(self):
        kwargs = super(TestFormView, self).get_form_kwargs()
        kwargs.update({
            'local_path': self.kwargs.get('path', '')
        })
        return kwargs

    def form_valid(self, form):
        form.execute()
        return super(TestFormView, self).form_valid(form)

    def get_success_url(self):
        return self.request.path


class FolderView(NextcloudConnectionViewMixin, TemplateView):
    template_name = "nextcloud_integration/folder_list.html"

    def get_context_data(self, **kwargs):
        context = super(FolderView, self).get_context_data(**kwargs)
        if self.kwargs.get('path', None):
            context['folders'] = get_object_or_404(NCFolder, path=self.kwargs['path'])
            context['files'] = context['folder'].ncfile_set.all()
        else:
            context['folders'] = NCFolder.objects.all()

        return context


class FolderMixin:
    """ Mixin that retrieves, stores and displays the NCFolder """
    def setup(self, request, *args, **kwargs):
        super(FolderMixin, self).setup(request, *args, **kwargs)
        self.folder = get_object_or_404(NCFolder, slug=kwargs.get('folder_slug', ''))

    def get_context_data(self, **kwargs):
        context = super(FolderMixin, self).get_context_data(**kwargs)
        context["folder"] = self.folder
        return context

class FolderContentView(NextcloudConnectionViewMixin, FolderMixin, TemplateView):
    template_name = "nextcloud_integration/folder_contents.html"


class FolderCreateView(NextcloudConnectionViewMixin, FormView):
    template_name = "nextcloud_integration/folder_add.html"
    form_class = FolderCreateForm
    success_url = reverse_lazy("nextcloud:folder_view")

    def form_valid(self, form):
        form.save()
        return super(FolderCreateView, self).form_valid(form)

class SynchFileToFolderView(NextcloudConnectionViewMixin, FolderMixin, FormView):
    template_name = "nextcloud_integration/synch_file_to_folder.html"
    form_class = SynchFileToFolderForm

    def get_form_kwargs(self):
        kwargs = super(SynchFileToFolderView, self).get_form_kwargs()
        kwargs["folder"] = self.folder
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(SynchFileToFolderView, self).form_valid(form)

    def form_invalid(self, form):
        return super(SynchFileToFolderView, self).form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            "nextcloud:folder_view",
            kwargs={
                'folder_slug': self.folder.slug,
            }
        )


class DownloadFileview(NextcloudConnectionViewMixin, SingleObjectMixin, View):
    template_name = "nextcloud_integration/file_download_test.html"
    model = NCFile
    slug_url_kwarg = "file_slug"
    slug_field = "slug"
    context_object_name = "file"

    def get(self, request, *args, **kwargs):
        self.file = get_object_or_404(
            NCFile,
            folder__slug = self.kwargs.get('folder_slug'),
            slug = self.kwargs.get('file_slug'),
        )
        file_data = self.get_file(self.file)

        response = HttpResponse(file_data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{self.file.file_name}"'

        return response

    def get_file(self, file):
        return self.client.download(file)

    def nextcloud_operation_failed(self, error: OperationFailed):
        msg = None
        if error.actual_code == 404:
            if not self.client.exists(self.file.folder.folder):
                # Set folder
                self.file.folder.is_missing = True
                self.file.folder.save(update_fields=["is_missing"])
                msg = "The folder could not be retrieved as it has been moved or renamed. " \
                      "It is unknown when it will be fixed as it needs to be addressed manually."
            elif not self.client.exists(self.file.file):
                self.file.is_missing = True
                self.file.save(update_fields=["is_missing"])
                msg = "The file could not be retrieved as it has been moved or renamed. " \
                      "It is unknown when it will be fixed as it needs to be addressed manually."
        if msg is None:
            msg = "Something unexpected occurred. Please inform the UUPS is this keeps occuring."
        error_msg(self.request, msg)

        return HttpResponseRedirect(redirect_to=reverse_lazy(
            "nextcloud:folder_view",
            kwargs={
                'folder_slug': self.file.folder.slug,
            }
        ))


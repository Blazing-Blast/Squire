from importlib import import_module
from typing import List, Optional, Type
from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.urls import reverse, include, path


__all__ = ['ViewCollectiveConfig', 'ViewCollectiveViewMixin', 'ViewCollectiveRegistry']


"""
A viewcollective is a collection of views from multiple modules united in one navigatable section.
Each part has it's own urlpattern containing one or more views so advanced uses can also be applied.
Tabs or any other front end url navigation can be used to move between the various parts.


"""




class ViewCollectiveConfig:
    """ This configures a section of the viewcollective with all relevant views and options. Any config should define:
    name: The name displayed in the tab
    icon_class: The icon classes that create the icon in a span element (e.g. by FontAwesome)
    url_name: The name of the url to navigate to.
    root_namespaces: The namespace where the root is in.
    url_keyword: url-string placed in the url to define this section

    Other options are:
    order_value: determines order in which the tabs are displayed (default 10)
    namespace: any additional namespace used for navigation.

    E.g.
    url_name = 'home'
    namespace = 'main'
    url_keyword = 'overview'
    has the tab navigate to reverse('main:home') which returns '/overview/<remainder of url path>'
    Note that the root namespace is already defined through the registry

    """
    name = None
    icon_class = ''
    url_name = None
    url_keyword = None
    order_value = 10

    """ Namespace for url. Can be left none. If not left none, know that url navigation will go like:
    accounts:<namespace>:url_name
    """
    namespace = None

    # Variables for basic requirements
    requires_login = True
    requires_membership = True

    def __init__(self, registry: 'ViewCollectiveRegistry'):
        self.registry = registry

    def is_accessible(self, request):
        """ Determines whether the given request allows this """
        if self.requires_login and not request.user.is_authenticated:
            return False
        if self.requires_membership and request.member is None:
            # TODO: limit to active members
            return False
        return True

    def is_enabled(self):
        """ Determines whether this config is active on start-up. Subclasses
            can override this to prevent loading views based on settings.
         """
        return True

    def get_urls(self):
        """ Builds a URLconf.
        When defining the view classes make sure they implement this config. Eg:
        > path('url_path/', views.MyMemberTabView.as_view(config=MyMemmberConfig))
        """
        raise NotImplementedError

    @property
    def urls(self):
        url_key = f'{self.url_keyword}/' if self.url_keyword else ''
        return path(url_key, (self.get_urls(), self.namespace, self.namespace))


class ViewCollectiveViewMixin:
    """
    Mixin for Views generated by a ViewCollectiveConfig
    """
    config: ViewCollectiveConfig = None

    def __init__(self, *args, config: Optional[ViewCollectiveConfig]=None, **kwargs):
        self.config = config or self.config
        if self.config is None:
            raise KeyError(f"{self.__class__.__name__} does not have a config linked did you forget to assign it "
                           f"in your urls in your config class? ({self.__class__.__name__}).as_view(config=self)")

        super(ViewCollectiveViewMixin, self).__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if not self.config.is_accessible(
            request=self.request,
            **self._get_other_check_kwargs()
        ):
            raise PermissionDenied()

        return super(ViewCollectiveViewMixin, self).dispatch(request, *args, **kwargs)

    def _get_other_check_kwargs(self):
        """
        Returns a dict with other kwargs for validation checks (e.g. association_group)
        :return:
        """
        return {}

    def get_context_data(self, **kwargs):
        return super(ViewCollectiveViewMixin, self).get_context_data(
            tabs=self.get_tabs(),
            **kwargs
        )

    def get_tabs(self):
        """
        Returns a list of dictionary objects for tab information
        :return:
        """
        registry = self.config.registry

        tabs = []
        applicable_configs = registry.get_applicable_configs(
            self.request,
            **self._get_other_check_kwargs()
        )
        for page_config in applicable_configs:
            tabs.append({
                'name': None, # redacted
                'verbose': page_config.name,
                'icon_class': page_config.icon_class,
                'url': self._get_tab_url(registry.namespace+':'+page_config.url_name),
                'selected': page_config == self.config,
            })
        return tabs

    def _get_tab_url(self, url_name, **url_kwargs):
        """ Returns the url for the tab. Interject url_kwargs to add extra perameters"""
        return reverse(url_name, kwargs=url_kwargs)



class ViewCollectiveRegistry:
    """ Registry class that regulates the various config classes defined """
    # Config root class to ensure config file validity
    config_class = ViewCollectiveConfig
    namespace = None

    def __init__(self, collective_namespace: str, folder_name: str, config_class: Type[ViewCollectiveConfig]=None):
        """
        Registry class that regulates access to all config classes
        :param collective_namespace: Name of the collective. Used for the namespace
        :param folder_name: the name of the folder in which the configs will be located
        :param config_class: Type of config classes being used
        """
        self.namespace = collective_namespace
        self.folder_name = folder_name
        self.config_class = config_class or self.config_class
        self._configs: List[ViewCollectiveConfig] = None

    def get_applicable_configs(self, request, **other_kwargs):
        """
        Returns a list of all applicable configs, i.e. filtered with request status and any other kwarg given
        :param request: The request containing the user and member instances of the session
        :param other_kwargs: keyword arguments related to the sequence of configs as defined in related config class
        :return: List of applicable confis
        """
        applicable_configs: List[ViewCollectiveConfig] = []
        for config in self.configs:
            if config.is_accessible(request, **other_kwargs):
                applicable_configs.append(config)
        return applicable_configs

    @property
    def configs(self):
        """ Returns a list of all related collective configs"""
        if self._configs is None:
            self._configs = self._get_configs()
        return self._configs

    def _get_configs(self):
        """ Constructs a list of all related collective configs """
        configs: List[ViewCollectiveConfig] = []

        # Go over all registered apps and check if it has a committee_pages config
        for app in apps.get_app_configs():
            try:
                module = import_module(f'{app.name}.{self.folder_name}.config')
            except ModuleNotFoundError:
                pass
            else:
                for name, cls in module.__dict__.items():
                    if isinstance(cls, type):
                        # Get all subclasses of the root config class, but not accidental imported copies of itself
                        if issubclass(cls, self.config_class) and cls != self.config_class:
                            config = cls(self)  # Initialise config
                            if config.is_enabled():
                                configs.append(config)
        return sorted(configs, key= lambda config: config.order_value)

    def get_urls(self, with_namespace=True):
        export_namespace = self.namespace if with_namespace else None

        urlpatterns = []
        for config in self.configs:
            urlpatterns.append(config.urls)

        return urlpatterns, export_namespace, export_namespace

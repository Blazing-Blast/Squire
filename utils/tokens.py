from typing import Type
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import Model
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

UserModel = get_user_model()


class TokenMixinBase:
    """
    The basis for a more general implementation of token verification in Django's `PasswordResetConfirmView`.
    This base class is used for both `UrlTokenMixin` and `SessionTokenMixin`; refer there for details.

    `fail_template_name`: Name of the template that is rendered whenever token verification fails.
    `session_token_name`: Name of the session token stored inside `django_session`
    `token_generator`: Token generator used to create and validate tokens. This should be different for each type
        of token (e.g. password reset, link account, etc.)
    `object_id_kwarg_name`: The url kwarg used to pass the base64-encoded id of the object
    `object_class`: The model class that objects passed to this view belong to. E.g. User for Django's password resets
    """

    # Subclasses should override this
    fail_template_name = "fail_template_name: TokenMixin fail placeholder"
    session_token_name: str = None
    token_generator: PasswordResetTokenGenerator = None
    object_id_kwarg_name = "uidb64"
    object_class: Type[Model] = UserModel

    def get_url_object(self, uidb64: str):
        """
        Decodes the base64-encoded id for an object of type `object_class` from the URL. If
        no object can be decoded, then `None` is returned instead.
        Equivalent to `PasswordResetConfirmView.get_user`
        """
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            url_object = self.object_class._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, self.object_class.DoesNotExist, ValidationError):
            url_object = None
        return url_object

    def delete_token(self):
        """Deletes the token from the session data"""
        del self.request.session[self.session_token_name]

    def dispatch(self, validlink, *args, **kwargs):
        # Render fail template if the URL is invalid
        if not validlink:
            return render(self.request, self.fail_template_name)
        return super().dispatch(*args, **kwargs)


class UrlTokenMixin(TokenMixinBase):
    """
    Stores a token passed through a URL in the session data. This allows it to be reused later, and
    avoids the possibility of leaking the token in the HTTP Referer header.

    This class generalizes Django's `PasswordResetConfirmView` token handling. The behaviour of
    `dispatch` is pretty much identical, but instead plugs in overridable methods and class variables
    to allow this mixin to be reused.

    Views using this mixin have a URL formatted like `foo/<base64-encoded-object-id>/<token>`, where the
    token is a long hash generated by the token generator. This hash contains various properties of the passed
    object that must have changed once the link/token should become invalid. In order to not leak the token,
    the token is first removed from the URL and replaced by `url_token_name`. The token is also saved in the
    session data so it can actually be used and verified later on.

    `url_token_name`: The value the token is set to in the URL once the token is stored in the session data.
                        Identical behaviour to `reset_url_token` in Django's `PasswordResetConfirmView`
    `token_kwarg_name`: The url kwarg used to pass the token
    """

    # Subclasses should override this
    url_token_name: str = None
    token_kwarg_name = "token"

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert self.object_id_kwarg_name in kwargs and self.token_kwarg_name in kwargs

        self.validlink = False
        self.url_object = self.get_url_object(kwargs[self.object_id_kwarg_name])

        # View is only valid if a url object was passed
        if self.url_object is not None:
            token = kwargs[self.token_kwarg_name]
            if token == self.url_token_name:
                session_token = self.request.session.get(self.session_token_name)
                if self.token_generator.check_token(self.url_object, session_token):
                    # If the token is valid, display the link account form.
                    self.validlink = True
                    return super().dispatch(self.validlink, *args, **kwargs)
            else:
                if self.token_generator.check_token(self.url_object, token):
                    # Store the token in the session and redirect to the
                    # link account form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.
                    self.request.session[self.session_token_name] = token
                    redirect_url = self.request.path.replace(token, self.url_token_name)
                    return HttpResponseRedirect(redirect_url)

        # Token was invalid
        return super().dispatch(self.validlink, *args, **kwargs)


class SessionTokenMixin(TokenMixinBase):
    """
    A more simplistic mixin that allows verifying a token already present in the session data.
    This mixin is thus only useful in combination with `UrlTokenMixin`. Specifically, only when a
    view using `UrlTokenMixin` redirects to a view using this mixin.

    This class generalizes a fraction of Django's `PasswordResetConfirmView` token handling. The behaviour of
    `dispatch` mimics the session token verification, but instead plugs in overridable methods and class variables
    to allow this mixin to be reused.
    """

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        assert self.object_id_kwarg_name in kwargs

        self.validlink = False
        self.url_object = self.get_url_object(kwargs[self.object_id_kwarg_name])

        # View is only valid if a url object was passed
        if self.url_object is not None:
            session_token = self.request.session.get(self.session_token_name)
            if self.token_generator.check_token(self.url_object, session_token):
                # If the token is valid, display the link account form.
                self.validlink = True
                return super().dispatch(self.validlink, *args, **kwargs)

        return super().dispatch(self.validlink, *args, **kwargs)

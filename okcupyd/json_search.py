import logging

import simplejson

from . import filter
from . import magicnumbers
from . import util
from .profile import Profile
from .session import Session


log = logging.getLogger(__name__)


search_filters = filter.Filters()


def SearchFetchable(session=None, **kwargs):
    """Search okcupid.com with the given parameters. Parameters are
    registered to this function through
    :meth:`~okcupyd.filter.Filters.register_filter_builder` of
    :data:`~okcupyd.json_search.search_filters`.

    :returns: A :class:`~okcupyd.util.fetchable.Fetchable` of
              :class:`~okcupyd.profile.Profile` instances.

    :param session: A logged in session.
    :type session: :class:`~okcupyd.session.Session`
    """
    session = session or Session.login()
    return util.Fetchable(
        SearchManager(
            SearchJSONFetcher(session, **kwargs),
            ProfileBuilder(session)
        )
    )


class SearchManager(object):

    def __init__(self, search_fetchable, profile_builder):
        self._search_fetchable = search_fetchable
        self._profile_builder = profile_builder
        self._last_after = None

    def fetch(self, count=18):
        last_last_after = object()
        while last_last_after != self._last_after:
            last_last_after = self._last_after
            for profile in self.fetch_once(count=count):
                yield profile

    def fetch_once(self, count=18):
        response = self._search_fetchable.fetch(
            after=self._last_after, count=count
        )
        try:
            self._last_after = response['paging']['cursors']['after']
        except KeyError:
            log.warning(simplejson.dumps(
                {
                    'msg': "unable to get after cursor from response",
                    'response': response
                }
            )
        )
        for profile in self._profile_builder(response):
            yield profile


class SearchJSONFetcher(object):

    def __init__(self, session=None, **options):
        self._session = session or Session.login()
        self._options = options
        self._parameters = search_filters.build(**options)

    def _query_params(self, after=None, count=None):
        search_parameters = {
            'after': after,
            'limit': count
        }
        search_parameters.update(self._parameters)
        return {'_json': search_parameters}

    def fetch(self, after=None, count=18):
        search_parameters = self._query_params(after=after, count=count)
        log.info(simplejson.dumps({'search_parameters': search_parameters}))
        response = self._session.okc_get(
            'search', params=search_parameters
        )
        try:
            search_json = response.json()
        except:
            log.warning(simplejson.dumps({'failure': response.content}))
            raise
        return search_json


class ProfileBuilder(object):

    def __init__(self, session):
        self._session = session

    def __call__(self, response_dictionary):
        try:
            profile_infos = response_dictionary['data']
        except KeyError:
            log.warning(simplejson.dumps(
                {
                    'msg': "unable to get data from response",
                    'response': response_dictionary
                }
            )
        )
        else:
            for profile_info in profile_infos:
                yield Profile(self._session, profile_info["username"])


class GentationFilter(search_filters.filter_class):

    def transform(gentation):
        return [
            magicnumbers.gentation_to_number.get(a_gentation.strip().lower(), a_gentation)
            for a_gentation in gentation
        ]

    descriptions = "A list of the allowable gentations of returned search results."
    types = list
    acceptable_values = magicnumbers.gentation_to_number.keys()


search_filters.add_to_docstring_of(SearchFetchable)

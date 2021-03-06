from zope.i18nmessageid import MessageFactory
from zope.interface import implements
from zope import schema
from zope.formlib import form
from AccessControl import SecurityManagement
from zope.component import getMultiAdapter, getUtility

from plone.memoize.instance import memoize
from plone.i18n.normalizer.interfaces import IIDNormalizer

from Products.ATContentTypes.permission import ChangeTopics
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName

# from plone.portlet.collection import collection as base
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base

from plone.app.form.widgets.uberselectionwidget import UberSelectionWidget
from plone.app.vocabularies.catalog import SearchableTextSourceBinder

from Products.ATContentTypes.interface import IATTopic

_ = MessageFactory('collective.carousel')


class ICarouselPortlet(IPortletDataProvider):
    """A portlet displaying a carousel with a Collection's results
    """

    header = schema.TextLine(
        title=_(u"Portlet header"),
        description=_(u"Title of the rendered portlet"),
        required=True)
        
    hideheader = schema.Bool(
        title=_(u"Don't show the header."),
        description=_(u"If enabled, the portlet will not show the header."),
        required=False,
        default=False)

    target_collection = schema.Choice(
        title=_(u"Target collection"),
        description=_(u"Find the collection which provides the items to list"),
        required=True,
        source=SearchableTextSourceBinder(
            {'object_provides': IATTopic.__identifier__},
            default_query='path:'))

    limit = schema.Int(
        title=_(u"Limit"),
        description=_(u"Specify the maximum number of items to show in the "
                      u"portlet. Leave this blank to show all items."),
        required=False)

    hide_controls = schema.Bool(
        title=_(u"Hide controls"),
        description=_(u"Tick this box if you want to temporarily hide "
                      "carousel controls i.e. next, prev, pause buttons."),
        required=True,
        default=False)

    timer = schema.Int(
        title=_(u"Timer"),
        description=_(u"How fast the carousel should be rotated \
                        (seconds)"),
        required=False,
        default=10)


class Assignment(base.Assignment):
    implements(ICarouselPortlet)

    header = u""
    hideheader = False
    target_collection=None
    limit = None
    hide_controls = False
    timer = 10

    def __init__(self, header=u"", hideheader = False, target_collection=None, limit=None,
                 hide_controls=False, timer=10):
        self.header = header
        self.hideheader = hideheader
        self.target_collection = target_collection
        self.limit = limit
        self.hide_controls = hide_controls
        self.timer = timer

    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen. Here, we use the title that the user gave.
        """
        return self.header or u"Carousel portlet"


class Renderer(base.Renderer):
    render = ViewPageTemplateFile('carousel.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

    @property
    def available(self):
        return len(self.results())

    def collection_url(self):
        collection = self.collection()
        if collection is None:
            return None
        else:
            return collection.absolute_url()

    def css_class(self):
        header = self.data.header
        normalizer = getUtility(IIDNormalizer)
        return "portlet-collection-%s" % normalizer.normalize(header)

    @memoize
    def results(self):
        results = []
        collection = self.collection()
        if collection is not None:
            limit = self.data.limit
            if limit and limit > 0:
                # pass on batching hints to the catalog
                results = collection.queryCatalog(batch=True, b_size=limit)
                results = results._sequence
            else:
                results = collection.queryCatalog()
            if limit and limit > 0:
                results = results[:limit]
        return results

    @memoize
    def collection(self):
        collection_path = self.data.target_collection
        if not collection_path:
            return None

        if collection_path.startswith('/'):
            collection_path = collection_path[1:]

        if not collection_path:
            return None

        portal_state = getMultiAdapter((self.context, self.request),
                                       name=u'plone_portal_state')
        portal = portal_state.portal()
        if isinstance(collection_path, unicode):
            # restrictedTraverse accepts only strings
            collection_path = str(collection_path)
        return portal.restrictedTraverse(collection_path, default=None)

    def use_view_action(self):
        pp = getToolByName(self.context, 'portal_properties', None)
        sp = getattr(pp, 'site_properties', None)
        use_view_action = sp.getProperty('typesUseViewActionInListings', ())
        return use_view_action

    def get_tile(self, obj):
        # When adapter is uesd this means we check whether obj has any special
        # instructions about how to be handled in defined view or interface
        # for multi adapter the same is true except more object than just the
        # obj are check for instructions

        #have to use traverse to make zpt security work
        tile = obj.unrestrictedTraverse("carousel-portlet-view")
        if tile is None:
            return None
        return tile()

    def canSeeEditLink(self):
        provider = self.collection()
        smanager = SecurityManagement.getSecurityManager()
        return smanager.checkPermission(ChangeTopics, provider)

    def editCarouselLink(self):
        provider = self.collection()
        if provider is not None:
            return provider.absolute_url() + '/criterion_edit_form'
        return None

    def getTimer(self):
        """ return timer in ms"""
        if getattr(self.data, 'timer', None) is not None:
            return int(self.data.timer*1000)
        else:
            return 10000

    def hideHeader(self):
        """ Whether we show the header or not """
        if self.data.hideheader:
            return True
        else:
            return False


class AddForm(base.AddForm):
    form_fields = form.Fields(ICarouselPortlet)
    form_fields['target_collection'].custom_widget = UberSelectionWidget

    label = _(u"Add Carousel Portlet")
    description = _(u"This portlet display a listing of items from a \
                      Collection as a carousel.")

    def create(self, data):
        return Assignment(**data)


class EditForm(base.EditForm):
    form_fields = form.Fields(ICarouselPortlet)
    form_fields['target_collection'].custom_widget = UberSelectionWidget

    label = _(u"Edit Carousel Portlet")
    description = _(u"This portlet display a listing of items from a \
                      Collection as a carousel.")

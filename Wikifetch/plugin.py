###
# Copyright (c) 2010, quantumlemur
# Copyright (c) 2011, Valentin Lorentz
# Copyright (c) 2015, James Lu
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###


import re
import sys
import lxml.html
import supybot.utils as utils
from supybot.commands import wrap, getopts, additional
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Wikifetch')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

if sys.version_info[0] >= 3:
    from urllib.parse import quote_plus
else:
    from urllib import quote_plus

class Wikifetch(callbacks.Plugin):
    """Grabs data from Wikipedia and other MediaWiki-powered sites."""
    threaded = True

    def _wiki(self, irc, msg, search, baseurl):
        """Fetches and replies content from a MediaWiki-powered website."""
        reply = ''

        # Different instances of MediaWiki use different URLs... This tries
        # to make the parser work for most sites, but still use resonable defaults
        # such as filling in http:// and appending /wiki to links...
        # Special cases: Wikia, Wikipedia, Wikimedia (i.e. Wikimedia Commons), Arch Linux Wiki
        if any(sitename in baseurl for sitename in ('wikia.com', 'wikipedia.org', 'wikimedia.org')):
            baseurl += '/wiki'
        elif 'wiki.archlinux.org' in baseurl:
            baseurl += '/index.php'
        if not baseurl.lower().startswith(('http://', 'https://')):
            baseurl = 'http://' + baseurl

        # first, we get the page
        addr = '%s/Special:Search?search=%s' % \
                    (baseurl, quote_plus(search))
        self.log.debug('Wikifetch: using URL %s', addr)
        article = utils.web.getUrl(addr)
        if sys.version_info[0] >= 3:
            article = article.decode()
        # parse the page
        tree = lxml.html.document_fromstring(article)
        # check if it gives a "Did you mean..." redirect
        didyoumean = tree.xpath('//div[@class="searchdidyoumean"]/a'
                                '[@title="Special:Search"]')
        if didyoumean:
            redirect = didyoumean[0].text_content().strip()
            if sys.version_info[0] < 3:
                if isinstance(redirect, unicode):
                    redirect = redirect.encode('utf-8','replace')
                if isinstance(search, unicode):
                    search = search.encode('utf-8','replace')
            if self.registryValue('showRedirects', msg.args[0]):
                reply += _('I didn\'t find anything for "%s". '
                           'Did you mean "%s"? ') % (search, redirect)
            addr = "%s/%s" % (baseurl,
                   didyoumean[0].get('href'))
            article = utils.web.getUrl(addr)
            if sys.version_info[0] >= 3:
                article = article.decode()
            tree = lxml.html.document_fromstring(article)
            search = redirect
        # check if it's a page of search results (rather than an article), and
        # if so, retrieve the first result
        searchresults = tree.xpath('//div[@class="searchresults"]/ul/li/a')
        if searchresults:
            redirect = searchresults[0].text_content().strip()
            if self.registryValue('showRedirects', msg.args[0]):
                reply += _('I didn\'t find anything for "%s", but here\'s the '
                           'result for "%s": ') % (search, redirect)
            addr = self.registryValue('url', msg.args[0]) + \
                   searchresults[0].get('href')
            article = utils.web.getUrl(addr)
            if sys.version_info[0] >= 3:
                article = article.decode()

            tree = lxml.html.document_fromstring(article)
            search = redirect
        # otherwise, simply return the title and whether it redirected
        elif self.registryValue('showRedirects', msg.args[0]):
            redirect = re.search('\(%s <a href=[^>]*>([^<]*)</a>\)' %
                                 _('Redirected from'), article)
            if redirect:
                try:
                    redirect = tree.xpath('//span[@class="mw-redirectedfrom"]/a')[0]
                    redirect = redirect.text_content().strip()
                    title = tree.xpath('//*[@class="firstHeading"]')
                    title = title[0].text_content().strip()
                    if sys.version_info[0] < 3:
                        if isinstance(title, unicode):
                            title = title.encode('utf-8','replace')
                        if isinstance(redirect, unicode):
                            redirect = redirect.encode('utf-8','replace')
                    reply += '"%s" (Redirected from "%s"): ' % (title, redirect)
                except IndexError:
                    pass
        # extract the address we got it from - most sites have the perm link
        # inside the page itself
        try:
            addr = tree.find(".//div[@class='printfooter']/a").attrib['href']
            addr = re.sub('([&?]|(amp;)?)oldid=\d+$', '', addr)
        except:
            pass
        # check if it's a disambiguation page
        disambig = tree.xpath('//table[@id="disambigbox"]') or \
            tree.xpath('//table[@id="setindexbox"]')
        if disambig:
            disambig = tree.xpath('//div[@id="bodyContent"]/div/ul/li')
            # Hackishly bold all <a> tags
            r = []
            for item in disambig:
                for link in item.findall('a'):
                    if link.text is not None:
                        link.text = "&#x02;%s&#x02;" % link.text
                item = item.text_content().replace('&#x02;', '\x02')
                # Normalize and strip whitespace, to prevent newlines and such
                # from corrupting the display.
                item = utils.str.normalizeWhitespace(item).strip()
                r.append(item)
            reply += format(_('%u is a disambiguation page. '
                       'Possible results include: %L'), addr, r)
        # or just as bad, a page listing events in that year
        elif re.search(_('This article is about the year [\d]*\. '
                       'For the [a-zA-Z ]* [\d]*, see'), article):
            reply += _('"%s" is a page full of events that happened in that '
                      'year.  If you were looking for information about the '
                      'number itself, try searching for "%s_(number)", but '
                      'don\'t expect anything useful...') % (search, search)
        # Catch talk pages
        elif 'ns-talk' in tree.find("body").attrib['class']:
            reply += format(_('This article appears to be a talk page: %u'), addr)
        else:
            p = tree.xpath("//div[@id='mw-content-text']/p[1]")
            if len(p) == 0 or 'wiki/Special:Search' in addr:
                if 'wikipedia:wikiproject' in addr.lower():
                    reply += format(_('This page appears to be a WikiProject page, '
                               'but it is too complex for us to parse: %u'), addr)
                else:
                    irc.error(_('Not found, or page malformed.'), Raise=True)
            else:
                p = p[0]
                # Replace <b> tags with IRC-style bold, this has to be
                # done indirectly because unescaped '\x02' is invalid in XML
                for b_tag in p.xpath('//b'):
                    b_tag.text = "&#x02;%s&#x02;" % (b_tag.text or '')
                p = p.text_content()
                p = p.replace('&#x02;', '\x02')
                # Get rid of newlines, etc., that can corrupt the output.
                p = utils.str.normalizeWhitespace(p)
                p = p.strip()
                if sys.version_info[0] < 3:
                    if isinstance(p, unicode):
                        p = p.encode('utf-8', 'replace')
                    if isinstance(reply, unicode):
                        reply = reply.encode('utf-8','replace')
                reply += format('%s %s %u', p, _('Retrieved from'), addr)
        reply = reply.replace('&amp;','&')

        # Remove inline citations (text[1][2][3], etc.)
        reply = re.sub('\[\d+\]', '', reply)

        return reply

    @internationalizeDocstring
    @wrap([getopts({'site': 'somethingWithoutSpaces'}), 'text'])
    def wiki(self, irc, msg, args, optlist, search):
        """[--site <site>] <search term>

        Returns the first paragraph of a wiki article. Optionally, a --site
        argument can be given to override the default (usually Wikipedia) -
        try using '--site lyrics.wikia.com' or '--site wiki.archlinux.org'."""
        optlist = dict(optlist)
        baseurl = optlist.get('site') or self.registryValue('url', msg.args[0])
        text = self._wiki(irc, msg, search, baseurl)

        irc.reply(text)

    @internationalizeDocstring
    @wrap([additional('somethingWithoutSpaces')])
    def random(self, irc, msg, args, site):
        """[<site>]

        Returns the first paragraph of a random wiki article. Optionally, the --site
        argument can be given to override the default (usually Wikipedia)."""
        baseurl = site or self.registryValue('url', msg.args[0])
        text = self._wiki(irc, msg, 'Special:Random', baseurl)

        irc.reply(text)

Class = Wikifetch


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

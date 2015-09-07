###
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

from supybot.test import *


class BonusLevelTestCase(PluginTestCase):
    plugins = ('BonusLevel',)

    @unittest.skipUnless(network, "Network-based tests have been disabled via "
                         "--no-network")
    def testLevelCommand(self):
        self.assertRegexp("level 1", "HELLO TONY & WOUTER")
        self.assertRegexp("level 1000", "Balancing Act")
        self.assertError("level 1337")  # No such level

    @unittest.skip("TODO: make this test work")
    def testLevelSnarfer(self):
        with conf.supybot.plugins.BonusLevel.enable.context(True):
            self.assertSnarfRegexp("test [lvlid=1]", "HELLO TONY & WOUTER")
            self.assertSnarfRegexp("lvlid=1000, without brackets", "Balancing Act")
            self.assertError("lvlid=1337")  # No such level
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

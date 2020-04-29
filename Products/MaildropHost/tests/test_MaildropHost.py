##############################################################################
#
# Copyright (c) 2004-2009 Jens Vagelpohl and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" MaildropHost tests

$Id: test_MaildropHost.py 1815 2009-10-09 21:14:55Z jens $
"""

import os
import shutil
import unittest

from Globals import package_home
from Products.MailHost.tests.testMailHost import TestMailHost

from Products.MaildropHost.MaildropHost import MaildropHost

TESTS_PATH = package_home(globals())

class DummyMaildropHost(MaildropHost):
    meta_type = 'Dummy Maildrop Host'
    def __init__(self, id):
        self.id = id
        self.sent = ''
    def _send(self, mfrom, mto, messageText, immediate=False):
        self.sent = messageText
        self.immediate = immediate

class MailHostConformanceTests(TestMailHost):
    # Test conformance to the standard MailHost objects by
    # running its tests against a MaildropHost object

    def _getTargetClass(self):
        return DummyMaildropHost


class MaildropHostTests(unittest.TestCase):

    def _getTargetClass(self):
        return MaildropHost

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_interfaces(self):
        from Products.MailHost.interfaces import IMailHost
        from zope.interface.verify import verifyClass
        verifyClass(IMailHost, self._getTargetClass())

    def test_instantiation(self):
        mdh = self._makeOne('MDH', 'MDH Title')
        self.assertEquals(mdh.getId(), 'MDH')
        self.assertEquals(mdh.title, 'MDH Title')
        self.assertEquals(mdh.isTransactional(), True)

    def test_edit(self):
        mdh = self._makeOne('MDH', 'MDH Title')

        # Make a change without specifying a new config file
        # path, the old path should stay the same
        config_path = mdh.getConfigPath()
        mdh.manage_makeChanges( 'New Title'
                              , transactional=False
                              )
        self.assertEquals(mdh.title, 'New Title')
        self.assertEquals(mdh.isTransactional(), False)
        self.assertEquals(mdh.getConfigPath(), config_path)

        # Now set a different configuration path
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        old_config_paths = CONFIG_PATHS
        dummyconfig_path = os.path.join(TESTS_PATH, 'dummyconfig')
        CONFIG_PATHS['foo_key'] = dummyconfig_path
        mdh.manage_makeChanges('Foo', path_key='foo_key')
        self.assertEqual(mdh.getConfigPath(), dummyconfig_path)

        # cleanup
        CONFIG_PATHS = old_config_paths

    def test_config_paths_default(self):
        mdh = self._makeOne('MDH', 'MDH Title')

        # Make sure the default key exists
        candidates = mdh.getCandidateConfigPaths()
        self.failUnless('DEFAULT' in [x[0] for x in candidates])

    def test_config_paths_set_unknown(self):
        mdh = self._makeOne('MDH', 'MDH Title')
        old_config = mdh.getConfigPath()

        # Must blow up if an invalid key is passed, config unchanged
        self.assertRaises(ValueError, mdh.setConfigPath, 'unknown')
        self.assertEquals(old_config, mdh.getConfigPath())

    def test_config_paths_set_invalid(self):
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        mdh = self._makeOne('MDH', 'MDH Title')
        old_config = mdh.getConfigPath()
        old_config_paths = CONFIG_PATHS
        CONFIG_PATHS['invalid'] = '/foo/bar/config'

        # Must blow up since the file does not exist, config unchanged
        self.assertRaises(ValueError, mdh.setConfigPath, 'invalid')
        self.assertEquals(old_config, mdh.getConfigPath())

        # cleanup
        CONFIG_PATHS = old_config_paths

    def test_config_paths_set_bad(self):
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        mdh = self._makeOne('MDH', 'MDH Title')
        old_config = mdh.getConfigPath()
        old_config_paths = CONFIG_PATHS
        bad_config_path = os.path.join(TESTS_PATH, 'badconfig')
        CONFIG_PATHS['bad'] = bad_config_path

        # Must blow up since the file does not exist
        self.assertRaises(RuntimeError, mdh.setConfigPath, 'bad')
        self.assertEquals(old_config, mdh.getConfigPath())

        # cleanup
        CONFIG_PATHS = old_config_paths

    def test_config_paths_set_good(self):
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        mdh = self._makeOne('MDH', 'MDH Title')
        old_smtp_host = mdh.smtp_host
        old_config_paths = CONFIG_PATHS
        good_config_path = os.path.join(TESTS_PATH, 'dummyconfig')
        CONFIG_PATHS['good'] = good_config_path

        # This must work, and the settings must stick
        mdh.setConfigPath('good')
        self.assertEquals(good_config_path, mdh.getConfigPath())
        self.assertNotEquals(old_smtp_host, mdh.smtp_host)
        self.assertEquals(mdh.smtp_host, 'this.is.a.test')

        # cleanup
        CONFIG_PATHS = old_config_paths

    def test_config_paths_and_delete(self):
        # What happens if the configuration file is deleted?
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        mdh = self._makeOne('MDH', 'MDH Title')
        old_smtp_host = mdh.smtp_host
        old_config_paths = CONFIG_PATHS
        dummy_config_path = os.path.join(TESTS_PATH, 'dummyconfig')
        new_config_path = os.path.join(TESTS_PATH, 'temporaryconfig')
        shutil.copyfile(dummy_config_path, new_config_path)
        CONFIG_PATHS['good'] = new_config_path

        # This must work, and the settings must stick
        mdh.setConfigPath('good')
        self.assertEquals(new_config_path, mdh.getConfigPath())
        self.assertEquals(mdh.smtp_host, 'this.is.a.test')

        # Now we delete the file and manually call up _load_config
        os.unlink(new_config_path)

        # If the config file is not found, the default config file is loaded.
        mdh._load_config()
        self.assertEquals(mdh.smtp_host, old_smtp_host)

        # cleanup
        CONFIG_PATHS = old_config_paths

    def testAddConfigPathMethod(self):
        from Products.MaildropHost.MaildropHost import CONFIG_PATHS
        old_config_paths = CONFIG_PATHS.copy()
        mdh = self._makeOne('MDH', 'MDH Title')
        candidates = mdh.getCandidateConfigPaths()
        # config paths may have been added elsewhere
        num_current_paths = len(candidates)
        config_path = '/a/system/path'
        mdh.addConfigPath('program_path', config_path)
        candidates = mdh.getCandidateConfigPaths()
        self.assertEquals(len(candidates), num_current_paths + 1)
        self.failUnless('program_path' in [x[0] for x in candidates])
        self.assertEquals(CONFIG_PATHS['program_path'], config_path)

        # cleanup
        CONFIG_PATHS = old_config_paths


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(MailHostConformanceTests),
        unittest.makeSuite(MaildropHostTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

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
""" MaildropHost is a transaction-aware asynchronous MailHost for Zope 2

$Id: MaildropHost.py 1815 2009-10-09 21:14:55Z jens $
"""

# General python imports
import os
from random import randint
from types import StringType
from types import UnicodeType
import urllib

# Zope imports
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import change_configuration
from Acquisition import aq_base
from App.config import getConfiguration
from Globals import DTMLFile
from Globals import InitializeClass
from Globals import package_home
from Products.MailHost.interfaces import IMailHost
from Products.MailHost.MailHost import MailHost
from zope.interface import implements

# MaildropHost package imports
from Products.MaildropHost.maildrop.stringparse import parse_assignments
from Products.MaildropHost.TransactionalMixin import TransactionalMixin

_globals = globals()
DEFAULT_CONFIG_PATH = os.path.join(package_home(globals()), 'config')

config = getattr(getConfiguration(),'product_config',{}).get('maildrophost', {})
CONFIG_PATHS = {'DEFAULT' : DEFAULT_CONFIG_PATH}
for key, value in config.items():
    if key.startswith('config-path'):
        CONFIG_PATHS[key] = value

addMaildropHostForm=DTMLFile('dtml/add', _globals)
def manage_addMaildropHost(self, id, title='Maildrop Host', REQUEST=None):
    """ add a MaildropHost into the system """
    mh = MaildropHost(id, title)
    self._setObject(id, mh)

    if REQUEST is not None:
        qs = 'manage_tabs_message=%s' % urllib.quote('Added MaildropHost.')
        ret_url = '%s/%s/manage_main?%s' % (self.absolute_url(), id, qs)
        REQUEST['RESPONSE'].redirect(ret_url)


def _makeTempPath(spool_path):
    """ Compute safe temp path based on provided spool dir path """
    temp_path = os.path.join(spool_path, str(randint(100000, 9999999)))

    while os.path.exists(temp_path):
        temp_path = os.path.join(spool_path, str(randint(100000, 9999999)))

    return temp_path
    

class MaildropHost(MailHost):
    """ A MaildropHost """

    implements(IMailHost)

    security = ClassSecurityInfo()
    meta_type = 'Maildrop Host'
    manage = manage_main = DTMLFile('dtml/edit', globals())
    manage_main._setName('manage_main')
    manage_log = DTMLFile('dtml/log', globals())

    manage_options = (
      ( { 'label' : 'Edit', 'action' : 'manage_main'
        , 'help' : ('MaildropHost', 'edit.stx')
        }
      , { 'label' : 'Maildrop Log', 'action' : 'manage_log'
        , 'help' : ('MaildropHost', 'log.stx')
        }
      )
      + MailHost.manage_options[1:]
      )

    def __init__(self, id='', title='Maildrop Host'):
        """ Initialize a new MaildropHost """
        self.id = id
        self.title = title
        self._transactional = True
        self._load_config()

    security.declareProtected(change_configuration, 'getConfigPath')
    def getConfigPath(self):
        """ Get the path to the currently active configuration file
        """
        return getattr(aq_base(self), 'config_path', DEFAULT_CONFIG_PATH)

    security.declareProtected(change_configuration, 'setConfigPath')
    def setConfigPath(self, path_key):
        """ Set the path to the currently active configuration file
        """
        config_path = CONFIG_PATHS.get(path_key, None)

        # Prevent passing in an invalid key, or maybe even a path
        if config_path is None:
            raise ValueError('Invalid path key %s' % path_key)

        # Make sure the provided configuration paths exist
        if not os.path.isfile(config_path):
            raise ValueError('Invalid config file path %s' % config_path)

        # Try to load the configuration to make sure we have a valid
        # configuration file.
        config = dict(parse_assignments(open(config_path).read()))
        for needed in ('SMTP_HOST', 'SMTP_PORT', 'MAILDROP_INTERVAL',
                       'MAILDROP_HOME', 'MAILDROP_TLS'):
            if config.get(needed, None) is None:
                raise RuntimeError('Invalid configuration file '
                                   'at %s' % config_path)

        # Persist the new path, and then reload the configuration
        self.config_path = CONFIG_PATHS.get(path_key)
        self._load_config()

    security.declareProtected(change_configuration, 'addConfigPath')
    def addConfigPath(self, path_key, path):
        """ Method to add a config path programmatically
        """
        CONFIG_PATHS[path_key] = path

    security.declareProtected(change_configuration, 'getCandidateConfigPaths')
    def getCandidateConfigPaths(self):
        """ Retrieve the config paths set in zope.conf
        """
        path_keys = CONFIG_PATHS.keys()
        path_keys.sort()
        return tuple([(x, CONFIG_PATHS.get(x)) for x in path_keys])

    def _load_config(self):
        """ Read the config info and store as object attributes """
        try:
            config = dict(parse_assignments(open(self.getConfigPath()).read()))
        except IOError:
            config = dict(parse_assignments(open(DEFAULT_CONFIG_PATH).read()))
        self.smtp_host = config['SMTP_HOST']
        self.smtp_port = config['SMTP_PORT']
        self.debug = config['DEBUG'] and 'On' or 'Off'
        self._debug_receiver = config.get('DEBUG_RECEIVER', '') 
        self.debug_receiver =  self._debug_receiver or '(not set)'
        self.polling = config['MAILDROP_INTERVAL']
        MAILDROP_HOME = config['MAILDROP_HOME']
        MAILDROP_SPOOL = config.get('MAILDROP_SPOOL', '')
        if MAILDROP_SPOOL:
            MAILDROP_SPOOLS = [x.strip() for x in MAILDROP_SPOOL.split(';')]
        else:
            MAILDROP_SPOOLS = [os.path.join(MAILDROP_HOME, 'spool')]
        self.spool = MAILDROP_SPOOLS[0]

        for spool in MAILDROP_SPOOLS:
            if not os.path.isdir(spool):
                os.makedirs(spool)

        MAILDROP_TLS = config['MAILDROP_TLS']
        self.use_tls = ( (MAILDROP_TLS > 1 and 'Forced') or
                         (MAILDROP_TLS == 1 and 'Yes') or
                         'No' )
        self.login = config['MAILDROP_LOGIN'] or '(not set)'
        self.password = config['MAILDROP_PASSWORD'] and '******' or '(not set)'
        self.add_messageid = config.get('ADD_MESSAGEID', 0) and 'On' or 'Off'
        MAILDROP_LOG_FILE = config.get('MAILDROP_LOG_FILE')
        if not MAILDROP_LOG_FILE:
            MAILDROP_VAR = config.get('MAILDROP_VAR',
                                      os.path.join(MAILDROP_HOME, 'var'))
            MAILDROP_LOG_FILE = os.path.join(MAILDROP_VAR, 'maildrop.log')
        self.maildrop_log_file = MAILDROP_LOG_FILE

    def __setstate__(self, state):
        """ load the config when we're loaded from the database """
        MailHost.__setstate__(self, state)
        self._load_config()

    def _makeTempPath(self):
        """ Helper to create a temp file name safely """
        return _makeTempPath(self.spool)

    security.declareProtected(change_configuration, 'manage_makeChanges')
    def manage_makeChanges( self
                          , title
                          , transactional=False
                          , path_key=None
                          , REQUEST=None
                          , **ignored
                          ):
        """ Change the MaildropHost properties """
        self.title = title
        self._transactional = not not transactional
        if path_key is not None:
            self.setConfigPath(path_key)

        if REQUEST is not None:
            msg = 'MaildropHost "%s" updated' % self.id
            return self.manage_main(manage_tabs_message=msg)


    security.declareProtected(change_configuration, 'isTransactional')
    def isTransactional(self):
        """ Is transactional mode in use? """
        return getattr(self, '_transactional', True)


    def _send(self, m_from, m_to, body, immediate=False):
        """ Send a mail using the asynchronous maildrop handler """
        if self._debug_receiver != '':
            m_to = self._debug_receiver
        if self.isTransactional():
            email = TransactionalEmail(m_from, m_to, body,
                                       self._makeTempPath())
        else:
            email = Email(m_from, m_to, body, self._makeTempPath())

        return email.send()


    security.declareProtected(change_configuration, 'getLog')
    def getLog(self, max_bytes=50000):
        """ Return the maildrop daemon log contents, up to max_bytes bytes.

        If the file path is invalid, return an empty string
        """
        if not os.path.isfile(self.maildrop_log_file):
            return ''

        log_handle = open(self.maildrop_log_file, 'r')
        log_data = log_handle.read(max_bytes)
        log_handle.close()

        return log_data


class Email:
    """ Simple non-persistent class to model a email message """

    def __init__(self, mfrom, mto, body, temp_path):
        """ Instantiate a new email object """
        if not (isinstance(mto, StringType) or isinstance(mto, UnicodeType)):
            self.m_to = ','.join(mto).replace('\r', '').replace('\n', '')
        else:
            self.m_to = mto.replace('\r', '').replace('\n', '')
        self.m_from = mfrom.replace('\r', '').replace('\n', '')
        self.body = body
        self._tempfile = temp_path
        self._transactional = False


    def send(self):
        """ Write myself to the file system """
        temp_path = self._tempfile
        lock_path = '%s.lck' % temp_path

        lock = open(lock_path, 'w')
        lock.write('locked')
        lock.close()

        temp = open(temp_path, 'w')
        temp.write(MAIL_TEMPLATE % (self.m_to, self.m_from, self.body))
        temp.close()

        if not self._transactional:
            os.unlink(lock_path)
        else:
            self._lockfile = lock_path

        # At this point only the lockfile path is interesting, try
        # to save some memory by gutting the object
        self.m_to = self.m_from = self.body = ''


class TransactionalEmail(TransactionalMixin, Email):
    """ Transaction-aware email class """

    def __init__(self, mfrom, mto, body, temp_path):
        """ Instantiate a new transactional email object """
        Email.__init__(self, mfrom, mto, body, temp_path)
        self._lockfile = ''
        self._transaction_done = 0
        self._transactional = True
        self._register()


MAIL_TEMPLATE = """##To:%s
##From:%s
%s
"""


InitializeClass(MaildropHost) 


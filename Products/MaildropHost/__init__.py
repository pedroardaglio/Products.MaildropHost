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
""" MaildropHost initialization

$Id: __init__.py 1696 2009-02-08 08:22:06Z jens $
"""

from AccessControl.Permissions import add_mailhost_objects
from Products.MaildropHost.MaildropHost import addMaildropHostForm
from Products.MaildropHost.MaildropHost import MaildropHost
from Products.MaildropHost.MaildropHost import manage_addMaildropHost

def initialize( context ):
    try:
        context.registerClass( MaildropHost
                             , permission=add_mailhost_objects
                             , constructors=( addMaildropHostForm
                                            , manage_addMaildropHost
                                            )
                             , icon='www/maildrop.gif'
                            )

        context.registerHelp()
        context.registerHelpTitle('MaildropHost')

    except:
        import traceback; traceback.print_exc()


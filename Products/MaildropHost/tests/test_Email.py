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
""" test_Email: contains MaildropHost email class tests

$Id: test_Email.py 1714 2009-03-02 10:05:36Z jens $
"""

import os
import shutil
import tempfile
import unittest
import warnings

from App.version_txt import getZopeVersion
import transaction


BODY = 'This is a test message'
ADDRESS_SEQUENCE = [ '"Root" <root@localhost>\r\n'
                   , '"Postmaster" <postmaster@localhost>'
                   ]
ADDRESS_STRING = '"Root" <root@localhost>\r'
ADDRESS_USTRING = u'"Postmaster" <postmaster@localhost>\n'


class EmailTestBase(unittest.TestCase):

    def _getTargetClass(self):
        # Must be specified in subclasses
        raise NotImplemented

    def _makeOne( self
                , mfrom=ADDRESS_USTRING
                , mto=ADDRESS_SEQUENCE
                , body=BODY
                ):
        from Products.MaildropHost.MaildropHost import _makeTempPath
        return self._getTargetClass()(mfrom,mto,body,_makeTempPath(self.spool))

    def setUp(self):
        self.spool = tempfile.mkdtemp()

    def _listSpools(self):
        return os.listdir(self.spool)

    def tearDown(self):
        shutil.rmtree(self.spool)

    def test_instantiation(self):
        email1 = self._makeOne()
        self.assertEquals( email1.m_to
                         , '"Root" <root@localhost>,'
                           '"Postmaster" <postmaster@localhost>'
                         )
        self.assertEquals(email1.m_from,u'"Postmaster" <postmaster@localhost>')
        self.assertEquals(email1.body, BODY)

        email2 = self._makeOne(mfrom=ADDRESS_STRING, mto=ADDRESS_USTRING)
        self.assertEquals(email2.m_to,u'"Postmaster" <postmaster@localhost>')
        self.assertEquals(email2.m_from, '"Root" <root@localhost>')
        self.assertEquals(email2.body, BODY)

        email3 = self._makeOne(mfrom=ADDRESS_USTRING, mto=ADDRESS_STRING)
        self.assertEquals(email3.m_to, '"Root" <root@localhost>')
        self.assertEquals(email3.m_from, u'"Postmaster" <postmaster@localhost>')
        self.assertEquals(email3.body, BODY)


class EmailTests(EmailTestBase):

    def _getTargetClass(self):
        from Products.MaildropHost.MaildropHost import Email
        return Email

    def test_send(self):
        # Non-transactional emails write to the spool no matter what
        self.assertEquals(len(self._listSpools()), 0)

        email = self._makeOne()
        email.send()

        # Now that the email has been sent, there should only be the 
        # actual email file. The lockfile should be gone.
        self.assertEquals(len(self._listSpools()), 1)

        # Make sure we clean up after ourselves...
        os.unlink(email._tempfile)
        self.assertEquals(len(self._listSpools()), 0)


class TransactionalEmailTests(EmailTestBase):

    def _getTargetClass(self):
        from Products.MaildropHost.MaildropHost import TransactionalEmail
        return TransactionalEmail


    def test_send_notransaction(self):
        # First of all, make sure we are in a clean transaction
        transaction.begin()

        # Transactional emails need a successful commit
        self.assertEquals(len(self._listSpools()), 0)
        email1 = self._makeOne()
        email1.send()
        email1_turd = email1._tempfile

        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # Make sure we clean up after ourselves...
        os.unlink(email1_turd)
        os.unlink('%s.lck' % email1_turd)
        self.assertEquals(len(self._listSpools()), 0)


    def test_send_transaction(self):
        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(self._listSpools()), 0)
        email1 = self._makeOne()
        email1.send()
        email1_turd = email1._tempfile

        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # Committing the transaction will remove the lock file so that the
        # maildrop daemon will process the mail file. That means only the
        # mail file itself remains in the spool after the commit.
        transaction.commit()
        self.assertEquals(len(self._listSpools()), 1)

        # Make sure we clean up after ourselves...
        os.unlink(email1_turd)
        self.assertEquals(len(self._listSpools()), 0)

        # abort the current transaction
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)


    def test_send_subtransaction(self):
        from Products.MaildropHost.TransactionalMixin import transactions

        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(transactions.keys()), 0)
        self.assertEquals(len(self._listSpools()), 0)
        email1 = self._makeOne()
        email1.send()

        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # Checking the transaction queue. A single transaction with a single
        # savepoint exists, which does not point to any other savepoints.
        self.assertEquals(len(transactions.keys()), 1)
        trans = transactions.values()[0]
        first_savepoint = trans._savepoint
        next = getattr(first_savepoint, 'next', None)
        previous = getattr(first_savepoint, 'previous', None)
        self.failUnless(next is None)
        self.failUnless(previous is None)

        # Committing a subtransaction should not do anything. Both email file
        # and lockfile should remain!
        transaction.savepoint(optimistic=True)
        self.assertEquals(len(self._listSpools()), 2)

        # The transaction queue still contains a single transaction, but we 
        # now have two savepoints pointing to each other.
        self.assertEquals(len(transactions.keys()), 1)
        trans = transactions.values()[0]
        second_savepoint = trans._savepoint
        next = getattr(second_savepoint, 'next', None)
        previous = getattr(second_savepoint, 'previous', None)
        self.failUnless(next is None)
        self.failUnless(previous is first_savepoint)
        self.failUnless(previous.next is second_savepoint)

        # Send another email and commit the subtransaction. Only the spool
        # file count changes.
        email2 = self._makeOne()
        email2.send()
        self.assertEquals(len(self._listSpools()), 4)
        self.assertEquals(len(transactions.keys()), 1)
        transaction.savepoint(optimistic=True)
        self.assertEquals(len(self._listSpools()), 4)

        # The transaction queue still contains a single transaction, but we 
        # now have three savepoints pointing to each other.
        self.assertEquals(len(transactions.keys()), 1)
        trans = transactions.values()[0]
        third_savepoint = trans._savepoint
        next = getattr(third_savepoint, 'next', None)
        previous = getattr(third_savepoint, 'previous', None)
        self.failUnless(next is None)
        self.failUnless(previous is second_savepoint)
        self.failUnless(previous.next is third_savepoint)

        # abort the current transaction, which will clean the spool as well
        # as the transactions mapping
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)
        self.assertEquals(len(transactions.keys()), 0)


    if getZopeVersion()[1] < 11 and getZopeVersion()[0] != -1:
        def test_send_subtransaction_oldstyle(self):
            from Products.MaildropHost.TransactionalMixin import transactions

            # Don't emit the DeprecationWarning we get
            warnings.filterwarnings('ignore', category=DeprecationWarning)

            # First of all, make sure we are in a clean transaction
            transaction.begin()

            self.assertEquals(len(transactions.keys()), 0)
            self.assertEquals(len(self._listSpools()), 0)
            email1 = self._makeOne()
            email1.send()

            # Now that the email has been sent, there should be two files: The
            # lock file and the actual email. The lockfile stays until the
            # transaction commits.
            self.assertEquals(len(self._listSpools()), 2)

            # Checking the transaction queue. A single transaction with a single
            # savepoint exists, which does not point to any other savepoints.
            self.assertEquals(len(transactions.keys()), 1)
            trans = transactions.values()[0]
            first_savepoint = trans._savepoint
            next = getattr(first_savepoint, 'next', None)
            previous = getattr(first_savepoint, 'previous', None)
            self.failUnless(next is None)
            self.failUnless(previous is None)

            # Committing a subtransaction should not do anything. Both email file
            # and lockfile should remain!
            transaction.commit(1)
            self.assertEquals(len(self._listSpools()), 2)

            # The transaction queue still contains a single transaction, but we 
            # now have two savepoints pointing to each other.
            self.assertEquals(len(transactions.keys()), 1)
            trans = transactions.values()[0]
            second_savepoint = trans._savepoint
            next = getattr(second_savepoint, 'next', None)
            previous = getattr(second_savepoint, 'previous', None)
            self.failUnless(next is None)
            self.failUnless(previous is first_savepoint)
            self.failUnless(previous.next is second_savepoint)

            # Send another email and commit the subtransaction. Only the spool
            # file count changes.
            email2 = self._makeOne()
            email2.send()
            self.assertEquals(len(self._listSpools()), 4)
            self.assertEquals(len(transactions.keys()), 1)
            transaction.commit(1)
            self.assertEquals(len(self._listSpools()), 4)

            # The transaction queue still contains a single transaction, but we 
            # now have three savepoints pointing to each other.
            self.assertEquals(len(transactions.keys()), 1)
            trans = transactions.values()[0]
            third_savepoint = trans._savepoint
            next = getattr(third_savepoint, 'next', None)
            previous = getattr(third_savepoint, 'previous', None)
            self.failUnless(next is None)
            self.failUnless(previous is second_savepoint)
            self.failUnless(previous.next is third_savepoint)

            # abort the current transaction, which will clean the spool as well
            transaction.abort()
            self.assertEquals(len(self._listSpools()), 0)
            self.assertEquals(len(transactions.keys()), 0)

            # Clean up warnfilter
            warnings.resetwarnings()


    def test_send_transaction_abort(self):
        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(self._listSpools()), 0)
        email1 = self._makeOne()
        email1.send()

        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # Aborting a transaction should remove the email file and the
        # lockfile.
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)


    def test_savepoints(self):
        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(self._listSpools()), 0)
        
        email1 = self._makeOne()
        email1.send()
        
        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.        
        self.assertEquals(len(self._listSpools()), 2)

        # create a savepoint
        savepoint1 = transaction.savepoint()

        # send a second mail
        email2 = self._makeOne()
        email2.send()
        self.assertEquals(len(self._listSpools()), 4)

        # create another savepoint
        savepoint2 = transaction.savepoint()
        
        # send a third mail
        email3 = self._makeOne()
        email3.send()
        self.assertEquals(len(self._listSpools()), 6)

        # rollback, this should remove email3
        savepoint2.rollback()        
        self.assertEquals(len(self._listSpools()), 4)

        # rollback again, this should remove email2
        savepoint1.rollback()        
        self.assertEquals(len(self._listSpools()), 2)
        
        # Aborting a transaction should remove the email file and the
        # lockfile.
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)


    def test_savepoints_earlier_rollback(self):
        from transaction.interfaces import InvalidSavepointRollbackError

        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(self._listSpools()), 0)

        email1 = self._makeOne()
        email1.send()
        
        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # create a savepoint
        savepoint1 = transaction.savepoint()
        
        # send a second mail
        email2 = self._makeOne()
        email2.send()
        self.assertEquals(len(self._listSpools()), 4)

        # create another savepoint
        savepoint2 = transaction.savepoint()
        
        # send a third mail
        email3 = self._makeOne()
        email3.send()
        self.assertEquals(len(self._listSpools()), 6)

        # rollback should remove email2 and email3
        savepoint1.rollback()        
        self.assertEquals(len(self._listSpools()), 2)

        # out of order rollback, should raise an exception
        self.assertRaises(InvalidSavepointRollbackError,
                          savepoint2.rollback)
        
        # Aborting a transaction should remove the email file and the
        # lockfile.
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)


    def test_savepoints_change_after_rollback(self):
        from transaction.interfaces import InvalidSavepointRollbackError

        # First of all, make sure we are in a clean transaction
        transaction.begin()

        self.assertEquals(len(self._listSpools()), 0)

        email1 = self._makeOne()
        email1.send()
        
        # Now that the email has been sent, there should be two files: The
        # lock file and the actual email. The lockfile stays until the
        # transaction commits.
        self.assertEquals(len(self._listSpools()), 2)

        # create a savepoint
        savepoint1 = transaction.savepoint()
        
        # send a second mail
        email2 = self._makeOne()
        email2.send()
        self.assertEquals(len(self._listSpools()), 4)

        # rollback should remove email2
        savepoint1.rollback()        
        self.assertEquals(len(self._listSpools()), 2)

        # send a third mail
        email3 = self._makeOne()
        email3.send()
        self.assertEquals(len(self._listSpools()), 4)

        # create another savepoint
        savepoint2 = transaction.savepoint()

        # rollback should remove email3
        savepoint1.rollback()        
        self.assertEquals(len(self._listSpools()), 2)

        # out of order rollback, should raise an exception
        self.assertRaises(InvalidSavepointRollbackError,
                          savepoint2.rollback)
        
        # Aborting a transaction should remove the email file and the lockfile.
        transaction.abort()
        self.assertEquals(len(self._listSpools()), 0)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(EmailTests),
        unittest.makeSuite(TransactionalEmailTests)
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


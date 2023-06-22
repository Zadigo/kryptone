import smtplib
from functools import cached_property
from smtplib import SMTP

from kryptone.conf import settings


class BaseEmailServer:
    """
    This is the base class used to create a
    an SMTP connection to a server.

    This class should not be used directly but subclassed
    in order to create a connection to a given SMTP server.

    >>> Gmail('test@gmail.com', 'xxx')
    """
    def __init__(self, host, port, user, password):
        try:
            # Create an SMTP object from host and port
            # :: <smtplib.SMTP> object
            smtp_connection = SMTP(host=host, port=port)
        except smtplib.SMTPConnectError:
            raise Exception('Could not connect to SMTP client')
        else:
            # Optional : Identify ourselves to
            # the server - normaly this is called
            # when .sendemail() is called
            smtp_connection.ehlo()
            # Put connection in TLS mode
            # (Transport Layer Security)
            smtp_connection.starttls()
            # It is advised by the documentation to
            # call EHLO after TLS [once again]
            smtp_connection.ehlo()

            try:
                smtp_connection.login(user, password)
            except smtplib.SMTPAuthenticationError:
                raise Exception('Could not login user to SMTP server')
            else:
                self.smtp_connection = smtp_connection

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    @cached_property
    def get_connection(self):
        return self.smtp_connection
                

class Gmail(BaseEmailServer):
    """
    A server set to be used with Gmail

    Description
    -----------

    In order for the connection to work, you should first
    allow your gmail account to accept third party programs.

    This can create a security warning that can be ignored.
    """
    def __init__(self, user, password):
        super().__init__('smtp.gmail.com', 587, user, password)


class Outlook(BaseEmailServer):
    """ 
    A server set to be used with Outlook
    """
    def __init__(self, user, password):
        super().__init__('SMTP.office365.com', 587, user, password)

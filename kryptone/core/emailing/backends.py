import smtplib
from functools import cached_property
from smtplib import SMTP

from kryptone.conf import settings


class BaseEmailServer:
    """
    This is the base class used to create a
    an SMTP connection to a server.

    Description
    -----------

    This class should not be used directly but subclassed
    in order to create a connection to a given SMTP server.
    """
    def __init__(self, host, port, user, password):
        try:
            # Create an SMTP object from host and port
            # :: <smtplib.SMTP> object
            smtp_connection = SMTP(host=host, port=port)
        except smtplib.SMTPConnectError:
            raise
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
                # Provided credentials are not good?
                # Get credentials from configuration
                # Raise an error since there's no purpose
                # using such an app without credentials
                # configuration = Configuration()
                # If user and password are none,
                # raises an ImproperlyConfiguredError()
                # user = configuration['USER']
                # password = configuration['PASSWORD']
                raise
            else:
                print(f'Logged in as {user} to {smtp_connection._host}.')
                self.smtp_connection = smtp_connection

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

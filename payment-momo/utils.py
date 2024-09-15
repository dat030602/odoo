# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_momo_partner_code(provider_sudo):
    """ Return the Partner Code for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The Partner Code
    :rtype: str
    """
    return provider_sudo.momo_partner_code


def get_momo_access_key(provider_sudo):
    """ Return the Access Key for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The Access Key
    :rtype: str
    """
    return provider_sudo.momo_access_key

def get_momo_public_key(provider_sudo):
    """ Return the Public Key for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The Public Key
    :rtype: str
    """
    return provider_sudo.momo_public_key


def get_momo_secret_key(provider_sudo):
    """ Return the Secret Key for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The Secret Key
    :rtype: str
    """
    return provider_sudo.momo_secret_key
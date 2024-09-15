# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_tmn_code(provider_sudo):
    """ Return the publishable key for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The publishable key
    :rtype: str
    """
    return provider_sudo.vnpay_tmn_code


def get_hash_secret_key(provider_sudo):
    """ Return the secret key for VNPay.

    Note: This method serves as a hook for modules that would fully implement VNPay Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The secret key
    :rtype: str
    """
    return provider_sudo.vnpay_hash_secret_key
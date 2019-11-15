from seaserv import ccnet_api
from seahub.profile.models import DetailedProfile
from seahub.group.utils import is_group_member, is_group_admin
from seahub.share.models import UserApprovalChain
from seahub.share.settings import PINGAN_COMPANY_SEAFILE_DEPT_MAP, \
        PINGAN_COMPANY_ID_NAME

def get_all_company():
    return ccnet_api.get_top_groups(including_org=False)

def get_company_id(username):
    d_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
    if d_profile and d_profile.company:
        company_id = d_profile.company
        return company_id.lower()
    else:
        return ''

def get_department_name(username):
    d_profile = DetailedProfile.objects.get_detailed_profile_by_user(username)
    if d_profile and d_profile.department:
        return d_profile.department
    else:
        return ''

def get_company_name(username):
    company_name = ''
    company_id = get_company_id(username)
    if company_id:
        if company_id in PINGAN_COMPANY_ID_NAME:
            company_name = PINGAN_COMPANY_ID_NAME[company_id]

    return company_name

def get_company_users(company_id):
    d_profiles = DetailedProfile.objects.filter(company=company_id)
    return [p.user for p in d_profiles]

def get_company_security(username):

    result = []
    company_id = get_company_id(username)
    if company_id in PINGAN_COMPANY_SEAFILE_DEPT_MAP:
        seafile_dept_id = PINGAN_COMPANY_SEAFILE_DEPT_MAP[company_id]
        members = ccnet_api.get_group_members(seafile_dept_id)
        result = [m.user_name for m in filter(lambda m: m.is_staff, members)]

    return result

def is_company_security(username):
    company_id = get_company_id(username)
    if company_id in PINGAN_COMPANY_SEAFILE_DEPT_MAP:
        seafile_dept_id = PINGAN_COMPANY_SEAFILE_DEPT_MAP[company_id]
        return is_group_admin(seafile_dept_id, username)
    else:
        return False

def is_company_member(username):
    company_id = get_company_id(username)
    if company_id in PINGAN_COMPANY_SEAFILE_DEPT_MAP:
        seafile_dept_id = PINGAN_COMPANY_SEAFILE_DEPT_MAP[company_id]
        return is_group_member(seafile_dept_id, username)
    else:
        return False

def has_security_in_chain_list(chain_list, company_security_list):
    for security in company_security_list:
        if security in chain_list[-1]:
            return True

    return False

def update_chain_list_when_group_member_updated(company_id, old_company_security_list):
    company_users = get_company_users(company_id)
    for user in company_users:
        chain_list = UserApprovalChain.objects.get_by_user(user)
        if chain_list:
            if has_security_in_chain_list(chain_list, old_company_security_list):
                new_chain_list = chain_list[:-1]
            else:
                new_chain_list = chain_list

            company_security_list = get_company_security(user)
            if company_security_list:
                company_security_list.insert(0, 'op_or')
                new_chain_list.append(company_security_list)

            UserApprovalChain.objects.filter(user=user).delete()
            UserApprovalChain.objects.create_chain(user, new_chain_list)

from seahub.utils.hasher import AESPasswordHasher
def check_password(password, encoded):
    return AESPasswordHasher().verify(password, encoded)

def user_in_chain(username, chain):
    """ chain could be:
        1. [('op_or', u'pa011-manager-1@1.com', u'1@1.com'), u'foo@foo.com', u'bar@bar.com']
        2. [u'lian@seafile.com']
    """

    if not username or len(chain) == 0:
        return False

    if username in chain:
        return True

    for sub_chain in chain:
        if username in sub_chain:
            return True

    return False

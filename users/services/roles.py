def is_super_admin(user):
    return user.is_superuser or user.groups.filter(name='super_admin').exists()


def is_company_admin(user):
    return user.groups.filter(name='company_admin').exists()


def get_role(user):
    if is_super_admin(user):
        return 'super_admin'
    if is_company_admin(user):
        return 'company_admin'
    return 'usuario'

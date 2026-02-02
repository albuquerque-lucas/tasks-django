def is_admin(user):
    return user.is_superuser or user.groups.filter(name='super_admin').exists()


def is_company_admin(user):
    return user.groups.filter(name='company_admin').exists()

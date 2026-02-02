def is_super_admin(user):
    return user.is_superuser or user.groups.filter(name='super_admin').exists()

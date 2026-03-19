from django.contrib.auth.models import AbstractUser
from djongo import models

class User(AbstractUser):
    email = models.EmailField(unique=True, blank=False, null=False)
    
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('OWNER', 'Owner'),
        ('USER', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')

    # Dùng username để đăng nhập chính
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username']


    def __str__(self):
        return f"{self.username} ({self.email})"
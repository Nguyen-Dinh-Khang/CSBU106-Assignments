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

    LOCATION_TYPE_CHOICES = (
        ('RESTAURANT', 'Nhà hàng'),
        ('ACCOMMODATION', 'Nơi ở (Khách sạn/Homestay)'),
        ('ENTERTAINMENT', 'Khu vui chơi'),
        ('NONE', 'Không có'),
    )
    type_location = models.CharField(
        max_length=20, 
        choices=LOCATION_TYPE_CHOICES, 
        default='NONE'
    )

    # Dùng username để đăng nhập chính
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username']


    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.email})"
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 1. Lấy chuỗi "Bearer <token>" từ Header Authorization
        auth_header = request.headers.get('Authorization')
        token = None

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # (Tùy chọn) Nếu không có trong Header mới tìm trong Cookie
        if not token:
            token = request.COOKIES.get('access_token')

        if token:
            try:
                # 2. Giải mã Access Token (SimpleJWT sẽ lo phần validate hết hạn)
                access_token = AccessToken(token)
                user_id = access_token['user_id']

                # 3. Gán user vào request để dùng ở các View
                request.user = User.objects.get(id=user_id)
            except Exception:
                # Nếu token giả, hết hạn hoặc ko có user_id -> coi như khách (Anonymous)
                pass
        
        return None
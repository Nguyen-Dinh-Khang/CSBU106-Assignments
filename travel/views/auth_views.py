from django.contrib.auth import authenticate
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from ..serializers import RestaurantSerializer, HotelSerializer, AttractionSerializer, UserSerializer, LocationSerializer, TravelInputSerializer, TravelOutputSerializer
from ..models import Restaurant, Hotel, Attraction, User, TravelInput, TravelOutput, Location


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    # 🔥 Chỉ cho phép user thấy chính mình
    def get_queryset(self):
        user = self.request.user
        # Nếu là Admin, cho phép thấy hết để quản lý
        if user.is_authenticated and user.role == 'ADMIN':
            return User.objects.all()
        
        # Nếu là User bình thường, chỉ thấy chính mình
        if user.is_authenticated:
            return User.objects.filter(id=user.id)
            
        # QUAN TRỌNG: Khi đăng ký (create), DRF vẫn cần truy cập vào 
        # queryset gốc để kiểm tra các ràng buộc dữ liệu.
        return User.objects.all()

    # 🔐 Phân quyền theo action
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]  # đăng ký
        return [IsAuthenticated()]  # còn lại phải login

    # 🔒 Chặn update/xóa người khác (extra safety)
    def perform_update(self, serializer):
        if serializer.instance != self.request.user:
            raise PermissionDenied("Bạn không thể sửa user khác")
        serializer.save()

    def perform_destroy(self, instance):
        if instance != self.request.user:
            raise PermissionDenied("Bạn không thể xóa user khác")
        instance.delete()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LoginView(APIView):
    # Cho phép mọi người truy cập không cần token
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # authenticate sẽ gọi qua EmailBackend của bạn
        user = authenticate(request, username=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            # Thêm thông tin bổ sung vào token nếu cần (như role)
            refresh['role'] = user.role 

            access = refresh.access_token
            access['role'] = user.role

            response = Response({
                "access": str(access),
                "user": {
                    "email": user.email,
                    "role": user.role,
                    "username": user.username
                }
            }, status=status.HTTP_200_OK)

            # Cài đặt Refresh Token vào HttpOnly Cookie để bảo mật
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax'
            )
            return response

        return Response({"error": "Email hoặc mật khẩu không chính xác"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    def post(self, request):
        response = Response({
            "message": "Đăng xuất thành công!"
        }, status=status.HTTP_200_OK)
        
        # Xóa cookie bằng cách đặt giá trị rỗng và hết hạn ngay lập tức
        response.delete_cookie('refresh_token')
        
        return response

class CustomTokenRefreshView(APIView):
    def post(self, request):
        # 1. Lấy refresh token từ trong Cookie ra
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({"error": "Vui lòng đăng nhập lại"}, status=401)
        
        try:
            # 2. Dùng thư viện SimpleJWT để verify và tạo access mới
            refresh = RefreshToken(refresh_token)
            access_token = refresh.access_token

            role = refresh.payload.get('role', 'USER')
            access_token['role'] = role

            data = {
                "access": str(access_token),
            }
            return Response(data, status=200)
        except TokenError:
            return Response({"error": "Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại"}, status=401)




from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserCreateSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar usuários.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """Autentica usuário e retorna token"""
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            
            if not username or not password:
                return Response({
                    'message': 'Credenciais incompletas',
                    'error_code': 'MISSING_CREDENTIALS',
                    'details': {
                        'username': 'Campo obrigatório' if not username else None,
                        'password': 'Campo obrigatório' if not password else None,
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = authenticate(username=username, password=password)
            if not user:
                return Response({
                    'message': 'Credenciais inválidas',
                    'error_code': 'INVALID_CREDENTIALS',
                    'details': None
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email
            })
        except Exception as e:
            return Response({
                'message': 'Erro ao processar login',
                'error_code': 'LOGIN_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def me(self, request):
        """Retorna os dados do usuário autenticado"""
        try:
            if not request.user.is_authenticated:
                return Response({
                    'message': 'Usuário não autenticado',
                    'error_code': 'UNAUTHENTICATED',
                    'details': None
                }, status=status.HTTP_401_UNAUTHORIZED)
            serializer = UserDetailSerializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            return Response({
                'message': 'Erro ao obter dados do usuário',
                'error_code': 'USER_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Permite registro de novo usuário"""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'message': 'Erro ao criar usuário',
                    'error_code': 'CREATION_ERROR',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'Erro de validação',
            'error_code': 'VALIDATION_ERROR',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



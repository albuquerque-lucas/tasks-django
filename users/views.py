import math
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination
from teams.models import Team
from auditlogs.utils import log_audit_event

from .serializers import UserCreateSerializer, UserDetailSerializer, UserSerializer
from safetodo.services.meili import search_users

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    """

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering_fields = [
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'phone',
        'date_joined',
        'last_login',
    ]
    ordering = ['-date_joined', '-id']

    def _parse_page_params(self, request):
        try:
            page = int(request.query_params.get('page', 1))
        except ValueError:
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 10))
        except ValueError:
            page_size = 10
        page = max(1, page)
        page_size = max(1, min(page_size, 500))
        return page, page_size

    def _get_ordering(self, request):
        ordering_param = request.query_params.get('ordering')
        if ordering_param:
            return [item.strip() for item in ordering_param.split(',') if item.strip()]
        return list(self.ordering or [])

    def _get_meili_sort(self, ordering):
        if not ordering:
            return ['id:desc']
        ordering_fields = set(self.ordering_fields or [])
        for item in ordering:
            field = item.lstrip('-')
            if field in ordering_fields:
                direction = 'desc' if item.startswith('-') else 'asc'
                return [f'{field}:{direction}']
        return ['id:desc']

    def _build_page_link(self, request, page):
        params = request.query_params.copy()
        params['page'] = page
        return request.build_absolute_uri(f'?{params.urlencode()}')

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search', '').strip()
        if not search_term:
            return super().list(request, *args, **kwargs)

        page, page_size = self._parse_page_params(request)
        ordering = self._get_ordering(request)
        meili_sort = self._get_meili_sort(ordering)
        offset = (page - 1) * page_size

        is_numeric = search_term.isdigit()
        filter_value = f'id = {int(search_term)}' if is_numeric else None
        query = '' if is_numeric else search_term

        try:
            meili_result = search_users(
                query=query,
                offset=offset,
                limit=page_size,
                sort=meili_sort,
                filter_value=filter_value,
            )
            hits = meili_result.get('hits', [])
            total = meili_result.get('estimatedTotalHits') or meili_result.get('nbHits') or 0
            ids = [item.get('id') for item in hits if item.get('id') is not None]
            if not ids:
                results = []
            else:
                preserved = Case(
                    *[When(id=pk, then=pos) for pos, pk in enumerate(ids)],
                    output_field=IntegerField(),
                )
                results = User.objects.filter(id__in=ids).order_by(preserved)

            serializer = self.get_serializer(results, many=True)
            total_pages = math.ceil(total / page_size) if page_size else 1
            next_link = self._build_page_link(request, page + 1) if page < total_pages else None
            prev_link = self._build_page_link(request, page - 1) if page > 1 else None
            response = Response(
                {
                    'count': total,
                    'next': next_link,
                    'previous': prev_link,
                    'results': serializer.data,
                }
            )
            response['X-Search-Provider'] = 'meili'
            return response
        except Exception:
            queryset = User.objects.all()
            search_filter = (
                Q(username__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
                | Q(phone__icontains=search_term)
            )
            if is_numeric:
                search_filter |= Q(id=int(search_term))
            queryset = queryset.filter(search_filter)

            valid_ordering = []
            ordering_fields = set(self.ordering_fields or [])
            for item in ordering:
                field = item.lstrip('-')
                if field in ordering_fields:
                    valid_ordering.append(item)
            if valid_ordering:
                queryset = queryset.order_by(*valid_ordering)
            elif self.ordering:
                queryset = queryset.order_by(*self.ordering)

            paginator = self.paginator
            page_data = paginator.paginate_queryset(queryset, request)
            response = paginator.get_paginated_response(
                self.get_serializer(page_data, many=True).data
            )
            response['X-Search-Provider'] = 'db'
            return response

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """Authenticate user and return JWT tokens."""
        try:
            username = request.data.get('username')
            password = request.data.get('password')

            if not username or not password:
                return Response(
                    {
                        'message': 'Credenciais incompletas',
                        'error_code': 'MISSING_CREDENTIALS',
                        'details': {
                            'username': 'Campo obrigatorio' if not username else None,
                            'password': 'Campo obrigatorio' if not password else None,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = authenticate(username=username, password=password)
            if not user:
                return Response(
                    {
                        'message': 'Credenciais invalidas',
                        'error_code': 'INVALID_CREDENTIALS',
                        'details': None,
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            refresh = RefreshToken.for_user(user)
            role = 'usuario'
            if user.is_superuser or user.groups.filter(name='super_admin').exists():
                role = 'super_admin'
            elif user.groups.filter(name='company_admin').exists():
                role = 'company_admin'
            return Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': role,
                }
            )
        except Exception as exc:
            return Response(
                {
                    'message': 'Erro ao processar login',
                    'error_code': 'LOGIN_ERROR',
                    'details': str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return authenticated user details."""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        'message': 'Usuario nao autenticado',
                        'error_code': 'UNAUTHENTICATED',
                        'details': None,
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            serializer = UserDetailSerializer(request.user)
            return Response(serializer.data)
        except Exception as exc:
            return Response(
                {
                    'message': 'Erro ao obter dados do usuario',
                    'error_code': 'USER_ERROR',
                    'details': str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path='notifications-seen')
    def notifications_seen(self, request):
        """Mark notifications as seen for badge purposes."""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        'message': 'Usuario nao autenticado',
                        'error_code': 'UNAUTHENTICATED',
                        'details': None,
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            now = timezone.now()
            request.user.notifications_last_seen_at = now
            request.user.save(update_fields=['notifications_last_seen_at'])
            return Response({'notifications_last_seen_at': now.isoformat()})
        except Exception as exc:
            return Response(
                {
                    'message': 'Erro ao atualizar notificacoes',
                    'error_code': 'NOTIFICATIONS_SEEN_ERROR',
                    'details': str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Allow new user registration."""
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                log_audit_event(
                    request,
                    action='user.register',
                    entity_type='User',
                    entity_id=user.id,
                    metadata={
                        'username': user.username,
                        'email': user.email,
                    },
                    user_override=user,
                )
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                        'user_id': user.id,
                        'username': user.username,
                        'email': user.email,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception as exc:
                return Response(
                    {
                        'message': 'Erro ao criar usuario',
                        'error_code': 'CREATION_ERROR',
                        'details': str(exc),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {
                'message': 'Erro de validacao',
                'error_code': 'VALIDATION_ERROR',
                'details': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def logout(self, request):
        """
        Logout idempotente: sempre retorna 200/204 mesmo sem auth.
        Se houver refresh token no body, apenas ignora por enquanto.
        """
        return Response({'message': 'Logout ok'}, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = serializer.save()
        log_audit_event(
            self.request,
            action='user.create',
            entity_type='User',
            entity_id=user.id,
            metadata={
                'username': user.username,
                'email': user.email,
            },
        )

    def perform_update(self, serializer):
        user = serializer.instance
        before = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': getattr(user, 'bio', None),
            'phone': getattr(user, 'phone', None),
        }
        user = serializer.save()
        after = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'bio': getattr(user, 'bio', None),
            'phone': getattr(user, 'phone', None),
        }
        changes = {
            key: {'from': before[key], 'to': after[key]}
            for key in before
            if before[key] != after[key]
        }
        if changes:
            log_audit_event(
                self.request,
                action='user.update',
                entity_type='User',
                entity_id=user.id,
                metadata={'changes': changes},
            )

    def perform_destroy(self, instance):
        log_audit_event(
            self.request,
            action='user.delete',
            entity_type='User',
            entity_id=instance.id,
            metadata={
                'username': instance.username,
                'email': instance.email,
            },
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Return simple user options."""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response(
                    {
                        'message': 'Usuario nao autenticado',
                        'error_code': 'UNAUTHENTICATED',
                        'details': None,
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            is_admin = user.is_superuser or user.groups.filter(name='super_admin').exists()
            is_company_admin = user.groups.filter(name='company_admin').exists()
            team_id = request.query_params.get('team')

            if team_id:
                team = Team.objects.filter(id=team_id).first()
                if not team:
                    return Response(
                        {
                            'message': 'Equipe nao encontrada',
                            'error_code': 'TEAM_NOT_FOUND',
                            'details': None,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if not (is_admin or is_company_admin or team.members.filter(id=user.id).exists() or team.managers.filter(id=user.id).exists()):
                    return Response(
                        {
                            'message': 'Usuario sem permissao para acessar equipe',
                            'error_code': 'FORBIDDEN',
                            'details': None,
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
                queryset = User.objects.filter(teams=team).distinct()
            else:
                queryset = (
                    User.objects.all()
                    if is_admin or is_company_admin
                    else User.objects.filter(id=user.id)
                )

            data = []
            for item in queryset:
                full_name = f'{item.first_name} {item.last_name}'.strip()
                data.append({'id': item.id, 'name': full_name or item.username})

            paginator = PageNumberPagination()
            try:
                page_size = int(request.query_params.get('page_size', 50))
            except ValueError:
                page_size = 50
            paginator.page_size = max(1, min(page_size, 500))
            page = paginator.paginate_queryset(data, request)
            return paginator.get_paginated_response(page)
        except Exception as exc:
            return Response(
                {
                    'message': 'Erro ao obter usuarios',
                    'error_code': 'USERS_ERROR',
                    'details': str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

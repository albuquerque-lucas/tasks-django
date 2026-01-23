from rest_framework.views import exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Handler customizado para exceções da API.
    Padroniza o formato de resposta de erros.
    """
    # Obtém a resposta padrão do DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Personaliza a resposta
        error_data = {
            'message': str(response.data) if isinstance(response.data, str) else 'Erro ao processar a requisição',
            'error_code': get_error_code(response.status_code, exc),
            'details': None
        }

        # Se há detalhes de validação
        if isinstance(response.data, dict):
            # Se tem campos específicos (validation errors)
            if any(isinstance(v, list) for v in response.data.values()):
                error_data['message'] = 'Erro de validação'
                error_data['details'] = response.data
            else:
                # Se é um erro genérico
                error_data['message'] = response.data.get('detail', 'Erro ao processar a requisição')
                if 'detail' in response.data:
                    del response.data['detail']
                if response.data:
                    error_data['details'] = response.data

        response.data = error_data

    return response


def get_error_code(status_code, exc):
    """Retorna um código de erro baseado no status HTTP"""
    code_map = {
        status.HTTP_400_BAD_REQUEST: 'VALIDATION_ERROR',
        status.HTTP_401_UNAUTHORIZED: 'UNAUTHORIZED',
        status.HTTP_403_FORBIDDEN: 'FORBIDDEN',
        status.HTTP_404_NOT_FOUND: 'NOT_FOUND',
        status.HTTP_409_CONFLICT: 'CONFLICT',
        status.HTTP_500_INTERNAL_SERVER_ERROR: 'INTERNAL_ERROR',
    }
    return code_map.get(status_code, 'ERROR')

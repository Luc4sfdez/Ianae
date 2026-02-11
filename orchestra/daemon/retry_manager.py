"""
Sistema de reintentos con backoff exponencial
Para llamadas a API Anthropic y otros servicios externos
"""

import time
import functools
from typing import Callable, Any, Tuple, Type, Optional
from structured_logger import get_logger

logger = get_logger("retry_manager")


class RetryExhausted(Exception):
    """Excepción cuando se agotan todos los reintentos"""
    pass


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorador para reintentar una función con backoff exponencial.

    Args:
        max_attempts: Número máximo de intentos (default: 3)
        initial_delay: Delay inicial en segundos (default: 1.0)
        backoff_factor: Factor de multiplicación del delay (default: 2.0)
        exceptions: Tupla de excepciones que provocan retry (default: todas)
        on_retry: Callback opcional llamado en cada retry (default: None)

    Ejemplo de delays:
        - Intento 1: 0s (inmediato)
        - Intento 2: 1s (1.0 * 2^0)
        - Intento 3: 2s (1.0 * 2^1)
        - Intento 4: 4s (1.0 * 2^2)

    Uso:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def call_api():
            return anthropic_client.messages.create(...)

    Con callback personalizado:
        def my_callback(attempt, error, delay):
            print(f"Retry {attempt} after {delay}s: {error}")

        @retry_with_backoff(max_attempts=5, on_retry=my_callback)
        def risky_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # Intentar ejecutar la función
                    result = func(*args, **kwargs)

                    # Éxito
                    if attempt > 1:
                        logger.info(
                            f"Función {func.__name__} exitosa en intento {attempt}",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts
                        )
                    return result

                except exceptions as e:
                    last_exception = e

                    # Si es el último intento, lanzar excepción
                    if attempt == max_attempts:
                        logger.error(
                            f"Todos los reintentos agotados para {func.__name__}",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                            error_type=type(e).__name__
                        )
                        raise RetryExhausted(
                            f"Agotados {max_attempts} intentos para {func.__name__}: {str(e)}"
                        ) from e

                    # Calcular delay con backoff exponencial
                    delay = initial_delay * (backoff_factor ** (attempt - 1))

                    # Log del retry
                    logger.warning(
                        f"Reintentando {func.__name__} en {delay}s (intento {attempt}/{max_attempts})",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                        error_type=type(e).__name__
                    )

                    # Callback personalizado si existe
                    if on_retry:
                        try:
                            on_retry(attempt, e, delay)
                        except Exception as callback_error:
                            logger.error(
                                "Error en callback on_retry",
                                callback_error=str(callback_error)
                            )

                    # Esperar antes del siguiente intento
                    time.sleep(delay)

            # Nunca debería llegar aquí, pero por si acaso
            raise RetryExhausted(
                f"Error inesperado en retry loop de {func.__name__}"
            ) from last_exception

        return wrapper
    return decorator


class APICallManager:
    """
    Manager para llamadas a API con retry, rate limiting y circuit breaker.

    Uso:
        api_manager = APICallManager(max_failures=3, cooldown_seconds=60)

        @api_manager.with_protection
        def call_anthropic():
            return client.messages.create(...)

        result = call_anthropic()
    """

    def __init__(self, max_failures: int = 3, cooldown_seconds: int = 60):
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_opened_at = None
        self.logger = get_logger("api_call_manager")

    def with_protection(self, func: Callable) -> Callable:
        """
        Decorador que combina retry + circuit breaker.

        Circuit breaker: Si hay N fallos consecutivos, abre el circuito
        durante X segundos (modo degradado).
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Verificar si el circuito está abierto
            if self.circuit_open:
                elapsed = time.time() - self.circuit_opened_at
                if elapsed < self.cooldown_seconds:
                    remaining = int(self.cooldown_seconds - elapsed)
                    self.logger.warning(
                        f"Circuit breaker abierto para {func.__name__}",
                        function=func.__name__,
                        remaining_seconds=remaining,
                        consecutive_failures=self.consecutive_failures
                    )
                    raise Exception(
                        f"Circuit breaker abierto. Reintente en {remaining}s"
                    )
                else:
                    # Cooldown terminado, cerrar circuito
                    self.circuit_open = False
                    self.consecutive_failures = 0
                    self.logger.info(
                        f"Circuit breaker cerrado para {func.__name__}",
                        function=func.__name__
                    )

            # Aplicar retry con backoff
            @retry_with_backoff(max_attempts=3, initial_delay=1.0)
            def protected_call():
                return func(*args, **kwargs)

            try:
                result = protected_call()

                # Éxito: resetear contador de fallos
                if self.consecutive_failures > 0:
                    self.logger.info(
                        f"Recuperado de {self.consecutive_failures} fallos",
                        function=func.__name__,
                        previous_failures=self.consecutive_failures
                    )
                    self.consecutive_failures = 0

                return result

            except Exception as e:
                # Fallo: incrementar contador
                self.consecutive_failures += 1

                # Si alcanza el límite, abrir circuito
                if self.consecutive_failures >= self.max_failures:
                    self.circuit_open = True
                    self.circuit_opened_at = time.time()

                    self.logger.critical(
                        f"Circuit breaker abierto tras {self.consecutive_failures} fallos",
                        function=func.__name__,
                        consecutive_failures=self.consecutive_failures,
                        cooldown_seconds=self.cooldown_seconds
                    )

                raise

        return wrapper


# Ejemplo de uso
if __name__ == "__main__":
    import random

    # Test 1: Retry simple
    @retry_with_backoff(max_attempts=4, initial_delay=0.5)
    def flaky_function():
        """Falla aleatoriamente para testing"""
        if random.random() < 0.7:  # 70% de fallo
            raise Exception("Fallo aleatorio")
        return "Éxito!"

    print("[TEST 1] Retry con backoff exponencial:")
    try:
        result = flaky_function()
        print(f"[OK] Resultado: {result}")
    except RetryExhausted as e:
        print(f"[ERROR] Agotados reintentos: {e}")

    print("\n" + "="*50 + "\n")

    # Test 2: Circuit breaker
    api_manager = APICallManager(max_failures=3, cooldown_seconds=5)

    @api_manager.with_protection
    def api_call():
        """Simula llamada a API que falla"""
        raise Exception("API temporalmente no disponible")

    print("[TEST 2] Circuit breaker:")
    for i in range(5):
        try:
            print(f"\n[{i+1}] Intentando llamar a API...")
            result = api_call()
            print(f"[OK] Resultado: {result}")
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(1)

    print("\n[OK] Tests completados. Revisar logs para ver formato estructurado.")

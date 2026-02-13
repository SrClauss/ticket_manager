import secrets
import string

# Base62 alphabet (letters + digits)
ALPHABET = string.ascii_letters + string.digits

def generate_token(length: int = 7) -> str:
    """Gera um token curto seguro usando letras e dígitos.

    Observação: tokens de 7 caracteres têm entropia limitada; use somente
    quando o escopo for controlado (apps privados, expiração, rate-limit).
    """
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))

"""
Crypto & domain constants for the messenger module.

All sizes follow MTProto 2.0-inspired spec:
- auth_key:  256-bit (32 bytes) — derived via ECDH X25519
- msg_key:   128-bit (16 bytes) — middle 128 bits of SHA-256
- aes_key:   256-bit (32 bytes)
- aes_iv:     96-bit (12 bytes) for GCM mode
"""

# ---------------------------------------------------------------------------
#  Key sizes (bytes)
# ---------------------------------------------------------------------------
AUTH_KEY_SIZE = 32          # 256-bit ECDH shared secret
MSG_KEY_SIZE = 16           # 128-bit message key
AES_KEY_SIZE = 32           # 256-bit AES key
AES_GCM_IV_SIZE = 12        # 96-bit IV for AES-GCM
X25519_PUBLIC_KEY_SIZE = 32  # X25519 public key

# ---------------------------------------------------------------------------
#  msg_key extraction from SHA-256 hash
# ---------------------------------------------------------------------------
MSG_KEY_OFFSET = 8           # Start byte in SHA-256 hash (bytes 8..23 = middle 128 bits)

# ---------------------------------------------------------------------------
#  Padding
# ---------------------------------------------------------------------------
PADDING_MIN = 12             # Minimum random padding bytes
PADDING_MAX = 1024           # Maximum random padding bytes
PADDING_BLOCK = 16           # Padded payload must be multiple of this

# ---------------------------------------------------------------------------
#  auth_key fragment offsets for KDF (direction-dependent)
# ---------------------------------------------------------------------------
# Initiator (side A) uses offset 0, Responder (side B) uses offset 8
AUTH_KEY_FRAGMENT_OFFSET_A = 0
AUTH_KEY_FRAGMENT_OFFSET_B = 8
AUTH_KEY_FRAGMENT_SIZE = 32   # 32-byte slice of auth_key for KDF

# ---------------------------------------------------------------------------
#  Room types
# ---------------------------------------------------------------------------
ROOM_TYPE_DIRECT = 'direct'
ROOM_TYPE_GROUP = 'group'
ROOM_TYPE_SECRET = 'secret'

ROOM_TYPE_CHOICES = [
    (ROOM_TYPE_DIRECT, 'Личный'),
    (ROOM_TYPE_GROUP, 'Групповой'),
    (ROOM_TYPE_SECRET, 'Секретный (E2EE)'),
]

# ---------------------------------------------------------------------------
#  Membership roles
# ---------------------------------------------------------------------------
ROLE_MEMBER = 'member'
ROLE_ADMIN = 'admin'
ROLE_OWNER = 'owner'

ROLE_CHOICES = [
    (ROLE_MEMBER, 'Участник'),
    (ROLE_ADMIN, 'Администратор'),
    (ROLE_OWNER, 'Владелец'),
]

# ---------------------------------------------------------------------------
#  Message types
# ---------------------------------------------------------------------------
MSG_TYPE_TEXT = 'text'
MSG_TYPE_FILE = 'file'
MSG_TYPE_SYSTEM = 'system'
MSG_TYPE_KEY_EXCHANGE = 'key_exchange'

MSG_TYPE_CHOICES = [
    (MSG_TYPE_TEXT, 'Текст'),
    (MSG_TYPE_FILE, 'Файл'),
    (MSG_TYPE_SYSTEM, 'Системное'),
    (MSG_TYPE_KEY_EXCHANGE, 'Обмен ключами'),
]

# ---------------------------------------------------------------------------
#  Sequence number limits
# ---------------------------------------------------------------------------
MAX_PTS = 2 ** 63 - 1        # Max pts value (BigInteger)

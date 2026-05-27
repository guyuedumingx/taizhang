"""
加密/解密工具：用于配置文件中的敏感信息（如数据库密码）加密存储。

纯 Python 标准库实现，不依赖任何第三方包。
使用 HMAC-SHA256 的 CTR 模式作为流密码。

使用方法：
  1. 设置环境变量 ENCRYPT_KEY（任意长度字符串）
  2. 加密：from app.core.crypto import encrypt; encrypt("my_password") → "ENC(xxxxx)"
  3. 解密：from app.core.crypto import decrypt; decrypt("ENC(xxxxx)") → "my_password"
  4. 生成密钥：python -m app.core.crypto --generate-key
  5. 命令行加密：ENCRYPT_KEY=xxx python -m app.core.crypto --encrypt "明文"
  6. 命令行解密：ENCRYPT_KEY=xxx python -m app.core.crypto --decrypt "密文"

密文格式：ENC(十六进制字符串)，方便在配置文件中识别哪些值是加密的。
"""
import hashlib
import hmac
import os
import secrets
import struct
import sys

# 默认密钥（环境变量 ENCRYPT_KEY 未设置时使用）
# 修改此处后，之前用旧密钥加密的数据将无法解密
_DEFAULT_KEY = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

# 密文前缀
CIPHER_PREFIX = "ENC("


def _get_key() -> bytes:
    """获取加密密钥，优先从环境变量读取，否则使用默认密钥。"""
    key = os.getenv("ENCRYPT_KEY", _DEFAULT_KEY)
    return key.encode("utf-8")


def _hmac_block(key: bytes, iv: bytes, counter: int) -> bytes:
    """用 HMAC-SHA256 生成一个 32 字节的伪随机块。"""
    return hmac.new(key, iv + struct.pack(">Q", counter), hashlib.sha256).digest()


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    """两个等长字节串异或。"""
    return bytes(x ^ y for x, y in zip(a, b))


def encrypt(plaintext: str) -> str:
    """
    加密字符串，返回格式为 ENC(十六进制密文)。

    流程：随机 IV → HMAC-CTR 生成密钥流 → XOR 加密 → IV + 密文拼接 → hex 编码
    """
    key = _get_key()
    iv = os.urandom(16)
    data = plaintext.encode("utf-8")

    # 生成密钥流并 XOR
    keystream = b""
    counter = 0
    while len(keystream) < len(data):
        keystream += _hmac_block(key, iv, counter)
        counter += 1

    ciphertext = _xor_bytes(data, keystream[:len(data)])
    hex_str = (iv + ciphertext).hex()
    return f"{CIPHER_PREFIX}{hex_str})"


def decrypt(ciphertext: str) -> str:
    """
    解密 ENC(十六进制密文) 格式的字符串，返回原始明文。

    如果输入不以 ENC( 开头或不是 ) 结尾，原样返回（兼容明文配置）。
    """
    if not ciphertext.startswith(CIPHER_PREFIX) or not ciphertext.endswith(")"):
        return ciphertext

    hex_str = ciphertext[len(CIPHER_PREFIX):-1]
    try:
        combined = bytes.fromhex(hex_str)
    except ValueError:
        raise ValueError("密文格式错误：不是有效的十六进制字符串")

    iv = combined[:16]
    ct = combined[16:]

    key = _get_key()

    # 生成同样的密钥流并 XOR（加密和解密操作相同）
    keystream = b""
    counter = 0
    while len(keystream) < len(ct):
        keystream += _hmac_block(key, iv, counter)
        counter += 1

    plaintext = _xor_bytes(ct, keystream[:len(ct)])
    return plaintext.decode("utf-8")


def is_encrypted(value: str) -> bool:
    """判断字符串是否为加密格式。"""
    return isinstance(value, str) and value.startswith(CIPHER_PREFIX) and value.endswith(")")


def generate_key() -> str:
    """生成一个随机密钥（64位十六进制字符串）。"""
    return secrets.token_hex(32)


if __name__ == "__main__":
    # 命令行运行时加载 .env 文件（向上查找 backend/.env 和项目根目录/.env）
    from dotenv import load_dotenv
    _base = os.path.dirname(os.path.abspath(__file__))  # backend/app/core
    _backend = os.path.dirname(os.path.dirname(_base))   # backend
    _project = os.path.dirname(_backend)                  # 项目根目录
    load_dotenv(os.path.join(_backend, ".env"))
    load_dotenv(os.path.join(_project, ".env"))

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-key":
        key = generate_key()
        print(f"生成的 ENCRYPT_KEY（请设置到环境变量中）:")
        print(f"ENCRYPT_KEY={key}")
        print()
        demo = "my_db_password_123"
        os.environ["ENCRYPT_KEY"] = key
        encrypted = encrypt(demo)
        decrypted = decrypt(encrypted)
        print(f"原文:   {demo}")
        print(f"密文:   {encrypted}")
        print(f"解密:   {decrypted}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--encrypt":
        if len(sys.argv) < 3:
            print("用法: python -m app.core.crypto --encrypt <明文>")
            sys.exit(1)
        if not os.getenv("ENCRYPT_KEY"):
            print("请先设置 ENCRYPT_KEY 环境变量")
            sys.exit(1)
        print(encrypt(sys.argv[2]))
    elif len(sys.argv) > 1 and sys.argv[1] == "--decrypt":
        if len(sys.argv) < 3:
            print("用法: python -m app.core.crypto --decrypt <密文>")
            sys.exit(1)
        if not os.getenv("ENCRYPT_KEY"):
            print("请先设置 ENCRYPT_KEY 环境变量")
            sys.exit(1)
        print(decrypt(sys.argv[2]))
    else:
        print("用法:")
        print("  python -m app.core.crypto --generate-key   生成密钥")
        print("  python -m app.core.crypto --encrypt <明文>  加密")
        print("  python -m app.core.crypto --decrypt <密文>  解密")

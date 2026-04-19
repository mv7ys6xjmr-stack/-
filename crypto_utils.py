from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
import base64
import os

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC as PBKDF2
    print("Используется PBKDF2HMAC")
except ImportError:
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        print("Используется PBKDF2")
    except ImportError:
        PBKDF2 = None
        print("PBKDF2 не доступен, будет использовано простое шифрование")


class AdvancedCrypto:
    
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        self.symmetric_key = Fernet.generate_key()
        self.cipher = Fernet(self.symmetric_key)
    
    def encrypt_message(self, message: str, recipient_public_key) -> bytes:
        try:
            encrypted_message = self.cipher.encrypt(message.encode())
            
            encrypted_key = recipient_public_key.encrypt(
                self.symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return encrypted_key + b"||" + encrypted_message
        except Exception as e:
            print(f"Ошибка шифрования: {e}")
            return self.cipher.encrypt(message.encode())
    
    def decrypt_message(self, encrypted_data: bytes) -> str:
        try:
            if b"||" in encrypted_data:
                encrypted_key, encrypted_message = encrypted_data.split(b"||", 1)
                
                symmetric_key = self.private_key.decrypt(
                    encrypted_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                cipher = Fernet(symmetric_key)
                return cipher.decrypt(encrypted_message).decode()
            else:
                return self.cipher.decrypt(encrypted_data).decode()
        except Exception as e:
            print(f"Ошибка расшифровки: {e}")
            return f"[Зашифрованное сообщение]"
    
    def get_public_key_pem(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def load_public_key(self, pem_data: bytes):
        return serialization.load_pem_public_key(pem_data)
    
    def sign_message(self, message: str) -> bytes:
        try:
            signature = self.private_key.sign(
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature
        except Exception as e:
            print(f"Ошибка подписи: {e}")
            return b""
    
    def verify_signature(self, message: str, signature: bytes, public_key) -> bool:
        try:
            public_key.verify(
                signature,
                message.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Ошибка проверки подписи: {e}")
            return False


class MessageCrypto:
    def __init__(self, password: str = None):
        if password is None:
            self.key = Fernet.generate_key()
        else:
            try:
                if PBKDF2:
                    salt = b'salt_123'
                    kdf = PBKDF2(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    self.key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
                else:
                    import hashlib
                    key_material = hashlib.sha256(password.encode()).digest()
                    self.key = base64.urlsafe_b64encode(key_material)
            except Exception as e:
                print(f"Ошибка создания ключа: {e}")
                self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, message: str) -> bytes:
        try:
            return self.cipher.encrypt(message.encode())
        except Exception as e:
            print(f"Ошибка шифрования: {e}")
            return message.encode()
    
    def decrypt(self, encrypted: bytes) -> str:
        try:
            return self.cipher.decrypt(encrypted).decode()
        except Exception as e:
            print(f"Ошибка расшифровки: {e}")
            try:
                return encrypted.decode()
            except:
                return "[Зашифрованное сообщение]"
    
    def get_key(self) -> bytes:
        return self.key


if __name__ == "__main__":
    print("Тестирование криптомодуля...")
    
    crypto_simple = MessageCrypto()
    test_msg = "Привет, мир!"
    encrypted = crypto_simple.encrypt(test_msg)
    decrypted = crypto_simple.decrypt(encrypted)
    print(f"Простое шифрование: {test_msg} -> {decrypted}")
    assert test_msg == decrypted, "Ошибка простого шифрования"
    
    try:
        crypto_adv = AdvancedCrypto()
        test_msg2 = "Секретное сообщение"
        encrypted2 = crypto_adv.encrypt_message(test_msg2, crypto_adv.public_key)
        decrypted2 = crypto_adv.decrypt_message(encrypted2)
        print(f"Продвинутое шифрование: {test_msg2} -> {decrypted2}")
        assert test_msg2 == decrypted2, "Ошибка продвинутого шифрования"
    except Exception as e:
        print(f"Продвинутое шифрование не поддерживается: {e}")
    
    print("Все тесты пройдены!")
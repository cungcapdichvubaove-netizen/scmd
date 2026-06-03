# -*- coding: utf-8 -*-
"""
Infrastructure Layer: Security Utilities.
Triển khai mã hóa AES-256 tuân thủ Nghị định 13/2023/NĐ-CP.
"""
import base64
import os
from django.conf import settings
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

def encrypt_aes256(plain_text: str) -> str:
    if not plain_text:
        return ""
    
    key = base64.b64decode(settings.FIELD_ENCRYPTION_KEY)
    iv = os.urandom(16)
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode()) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    cipher_text = encryptor.update(padded_data) + encryptor.finalize()
    
    # Kết quả: iv + cipher_text (Base64)
    return base64.b64encode(iv + cipher_text).decode('utf-8')

def decrypt_aes256(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    
    try:
        data = base64.b64decode(encrypted_text)
        iv = data[:16]
        cipher_text = data[16:]
        
        key = base64.b64decode(settings.FIELD_ENCRYPTION_KEY)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(cipher_text) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        plain_text = unpadder.update(padded_data) + unpadder.finalize()
        
        return plain_text.decode('utf-8')
    except Exception:
        return "[DECRYPTION_ERROR]"
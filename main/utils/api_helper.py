# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
SCMD Pro
=======
Security Command (SCMD) System
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: main/utils/api_helper.py
Author: Mr. Anh
Created Date: 2025-12-10
Description: Tiện ích hỗ trợ phản hồi API chuẩn hóa (Standard API Response).
             Giúp Mobile Team không phải đoán định dạng trả về.
"""

from rest_framework.response import Response
from rest_framework import status

def api_response(data=None, message="Success", success=True, status_code=status.HTTP_200_OK, error_code=None):
    """
    Hàm wrapper để trả về response chuẩn:
    {
        "success": true,
        "message": "...",
        "data": { ... },
        "error_code": null
    }
    """
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {},
    }
    
    if not success and error_code:
        payload["error_code"] = error_code
        
    return Response(payload, status=status_code)

def error_response(message="Error", error_code="SERVER_ERROR", status_code=status.HTTP_400_BAD_REQUEST, errors=None):
    """
    Trả về lỗi chuẩn. Tham số `errors` dùng để chứa chi tiết lỗi validation.
    """
    return api_response(
        success=False,
        message=message,
        data=errors, # Trả về chi tiết lỗi field (nếu có) vào field data
        status_code=status_code,
        error_code=error_code
    )
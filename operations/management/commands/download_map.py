# -*- coding: utf-8 -*-
"""
Security Command (SCMD) System
------------------------------
Copyright (c) 2025 SCMD.co.ltd. All Rights Reserved.

File: operations/management/commands/download_map.py
Author: Mr. Anh
Created Date: 2025-12-02
Description: Tool tự động tải bản đồ về Cache Local.
             Chạy 1 lần - Dùng mãi mãi (Kể cả mất mạng).
             
             Usage: python manage.py download_map --lat=21.0285 --lng=105.8542 --zoom=12
"""

import os
import requests
import time
import math
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Tải bản đồ Offline về Server.'

    def add_arguments(self, parser):
        parser.add_argument('--lat', type=float, default=21.0285, help='Vĩ độ tâm (Default: Hà Nội)')
        parser.add_argument('--lng', type=float, default=105.8542, help='Kinh độ tâm')
        parser.add_argument('--zoom', type=int, default=13, help='Mức zoom cần tải (10-18)')
        parser.add_argument('--radius', type=int, default=2, help='Bán kính tải (km)')

    def handle(self, *args, **options):
        lat_center = options['lat']
        lng_center = options['lng']
        zoom = options['zoom']
        radius = options['radius']

        self.stdout.write(f"🌍 Bắt đầu tải bản đồ khu vực: {lat_center}, {lng_center} (Zoom: {zoom})")

        # Tính toán khoảng cách tile (x, y)
        n = 2 ** zoom
        xtile_center = n * ((lng_center + 180) / 360)
        ytile_center = n * (1 - (math.log(math.tan(math.radians(lat_center)) + (1 / math.cos(math.radians(lat_center)))) / math.pi)) / 2
        
        # Bán kính khoảng 2-3 tile xung quanh tâm
        range_tile = 3 
        
        total = (range_tile * 2 + 1) ** 2
        count = 0

        for x in range(int(xtile_center) - range_tile, int(xtile_center) + range_tile + 1):
            for y in range(int(ytile_center) - range_tile, int(ytile_center) + range_tile + 1):
                self.download_tile(zoom, x, y)
                count += 1
                self.stdout.write(f"⬇️  Đã tải {count}/{total} ảnh...", ending='\r')
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Đã tải xong {count} ảnh bản đồ Offline!"))

    def download_tile(self, z, x, y):
        url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        tile_dir = os.path.join(settings.MEDIA_ROOT, 'map_tiles', str(z), str(x))
        tile_path = os.path.join(tile_dir, f"{y}.png")

        if os.path.exists(tile_path):
            return # Đã có thì bỏ qua

        try:
            headers = {'User-Agent': 'SCMD-Downloader/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                if not os.path.exists(tile_dir):
                    os.makedirs(tile_dir)
                with open(tile_path, 'wb') as f:
                    f.write(response.content)
            time.sleep(0.1) # Lịch sự với server OSM
        except:
            pass
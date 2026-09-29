#!/usr/bin/env python3
"""
Downloads and vendors third-party client-side libraries into assets/vendor/.
Ensures the entire application can run completely offline without external CDNs.
Total vendored size is approximately 1.1 MB (well below the 5 MB repository budget).
"""

import os
import sys
import urllib.request
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(BASE_DIR, 'assets', 'vendor')

ASSETS = [
    # Leaflet 1.9.4
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'leaflet.js'),
        'sha256': 'db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a'
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'leaflet.css'),
        'sha256': 'a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6'
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-icon.png'),
        'sha256': '574c3a5cca85f4114085b6841596d62f00d7c892c7b03f28cbfa301deb1dc437'
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-icon-2x.png'),
        'sha256': '00179c4c1ee830d3a108412ae0d294f55776cfeb085c60129a39aa6fc4ae2528'
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-shadow.png'),
        'sha256': '264f5c640339f042dd729062cfc04c17f8ea0f29882b538e3848ed8f10edb4da'
    },
    # Chart.js 4.4.1
    {
        'url': 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
        'dest': os.path.join(VENDOR_DIR, 'chartjs', 'chart.umd.min.js'),
        'sha256': 'd2af8974e95271638772e9e9524db5b9a6f58d6ec2d5d781400447b4a31c681e'
    },
    # jsPDF 2.5.1
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
        'dest': os.path.join(VENDOR_DIR, 'jspdf', 'jspdf.umd.min.js'),
        'sha256': '98ccf17aa10c20bb1301762618fcc9b6ab3a4e7f26b6071d64d0b41154df3875'
    },
    # html2canvas 1.4.1
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
        'dest': os.path.join(VENDOR_DIR, 'html2canvas', 'html2canvas.min.js'),
        'sha256': 'e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb'
    },
    # jsPDF-AutoTable 3.8.2
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js',
        'dest': os.path.join(VENDOR_DIR, 'jspdf-autotable', 'jspdf.plugin.autotable.min.js'),
        'sha256': '27a9c3b61843c6312b87f142d40fe77c0f0f054c9f3cdeccc4bfd5f3322859c8'
    }
]

def download_assets():
    headers = {'User-Agent': 'DCMissedCollectionAnalysis/1.0'}
    total_downloaded = 0
    print(f"Vendoring third-party assets to {VENDOR_DIR}...")
    for item in ASSETS:
        dest = item['dest']
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            sz = os.path.getsize(dest)
            total_downloaded += sz
            print(f" - Already present: {os.path.relpath(dest, BASE_DIR)} ({sz // 1024} KB)")
            continue

        url = item['url']
        expected_sha256 = item.get('sha256')
        print(f" - Downloading: {url} -> {os.path.relpath(dest, BASE_DIR)}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(dest, 'wb') as out_f:
            data = resp.read()
            out_f.write(data)
            sz = len(data)
            total_downloaded += sz
            print(f"   Done ({sz // 1024} KB)")

        if expected_sha256:
            with open(dest, 'rb') as f:
                actual_sha256 = hashlib.sha256(f.read()).hexdigest()
            if actual_sha256 != expected_sha256:
                os.remove(dest)
                raise ValueError(f"SHA256 mismatch for {dest}. Expected: {expected_sha256}, actual: {actual_sha256}")

    print(f"Total vendored footprint: {total_downloaded // 1024} KB ({total_downloaded / (1024*1024):.2f} MB)")

if __name__ == '__main__':
    download_assets()

#!/usr/bin/env python3
"""
Downloads and vendors third-party client-side libraries into assets/vendor/.
Ensures the entire application can run completely offline without external CDNs.
Total vendored size is approximately 1.1 MB (well below the 5 MB repository budget).
"""

import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(BASE_DIR, 'assets', 'vendor')

ASSETS = [
    # Leaflet 1.9.4
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'leaflet.js')
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'leaflet.css')
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-icon.png')
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-icon-2x.png')
    },
    {
        'url': 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        'dest': os.path.join(VENDOR_DIR, 'leaflet', 'images', 'marker-shadow.png')
    },
    # Chart.js 4.4.1
    {
        'url': 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
        'dest': os.path.join(VENDOR_DIR, 'chartjs', 'chart.umd.min.js')
    },
    # jsPDF 2.5.1
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
        'dest': os.path.join(VENDOR_DIR, 'jspdf', 'jspdf.umd.min.js')
    },
    # html2canvas 1.4.1
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
        'dest': os.path.join(VENDOR_DIR, 'html2canvas', 'html2canvas.min.js')
    },
    # jsPDF-AutoTable 3.8.2
    {
        'url': 'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js',
        'dest': os.path.join(VENDOR_DIR, 'jspdf-autotable', 'jspdf.plugin.autotable.min.js')
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
        print(f" - Downloading: {url} -> {os.path.relpath(dest, BASE_DIR)}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(dest, 'wb') as out_f:
            data = resp.read()
            out_f.write(data)
            sz = len(data)
            total_downloaded += sz
            print(f"   Done ({sz // 1024} KB)")

    print(f"Total vendored footprint: {total_downloaded // 1024} KB ({total_downloaded / (1024*1024):.2f} MB)")

if __name__ == '__main__':
    download_assets()

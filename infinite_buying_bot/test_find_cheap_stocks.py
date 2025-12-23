"""
저가 미국주식 조회 및 테스트
- 1주당 $35 미만 (약 5만원) 종목 찾기
- 잔고 확인 및 환전 여부 확인
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf

print("\n" + "="*70)
print("  📊 저가 미국주식 조회 ($35 미만)")
print("="*70)

# 테스트 가능한 저가 주식 목록
cheap_stocks = [
    ("F", "Ford Motor"),
    ("PLTR", "Palantir"),
    ("SOFI", "SoFi"),
    ("NIO", "NIO"),
    ("RIVN", "Rivian"),
    ("LCID", "Lucid"),
    ("SNAP", "Snap"),
    ("CCL", "Carnival"),
    ("AAL", "American Airlines"),
    ("GRAB", "Grab"),
    ("NU", "Nu Holdings"),
    ("PINS", "Pinterest"),
]

print(f"\n{'종목':<8} {'이름':<20} {'현재가':>10}")
print("-"*45)

affordable = []
for symbol, name in cheap_stocks:
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        if price and price < 35:
            affordable.append((symbol, name, price))
            print(f"{symbol:<8} {name:<20} ${price:>8.2f}")
    except:
        pass
    time.sleep(0.2)

print("-"*45)
print(f"\n✅ $35 미만 종목 {len(affordable)}개 발견")

if affordable:
    # 가장 저렴한 종목 선택
    cheapest = min(affordable, key=lambda x: x[2])
    print(f"\n🎯 추천 테스트 종목: {cheapest[0]} ({cheapest[1]}) - ${cheapest[2]:.2f}")

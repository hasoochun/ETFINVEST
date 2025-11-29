"""
한국투자증권 모의투자 API 진단 스크립트
- API 연결 테스트
- 잔고 조회 상세 로그
- 주문 실행 테스트
- 응답 데이터 구조 분석
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Configure detailed logging
log_file = os.path.join(os.path.dirname(__file__), 'logs', f'api_diagnosis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import KIS API modules
from infinite_buying_bot.api import kis_api as api
from infinite_buying_bot.api import kis_auth as ka

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)
    logger.info(f"=== {title} ===")

def log_dataframe(df, name):
    """Log DataFrame details"""
    if df is None:
        logger.warning(f"{name}: DataFrame is None")
        print(f"❌ {name}: None")
        return
    
    if df.empty:
        logger.warning(f"{name}: DataFrame is EMPTY")
        print(f"⚠️  {name}: EMPTY DataFrame")
    else:
        logger.info(f"{name}: {len(df)} rows, {len(df.columns)} columns")
        print(f"✅ {name}: {len(df)} rows, {len(df.columns)} columns")
        
        # Log columns
        logger.info(f"{name} Columns: {df.columns.tolist()}")
        print(f"   Columns: {df.columns.tolist()[:10]}{'...' if len(df.columns) > 10 else ''}")
        
        # Log first row
        if len(df) > 0:
            logger.info(f"{name} First Row:\n{df.iloc[0].to_dict()}")
            print(f"   First Row (sample):")
            for key, value in list(df.iloc[0].to_dict().items())[:5]:
                print(f"     {key}: {value}")
            if len(df.iloc[0]) > 5:
                print(f"     ... ({len(df.iloc[0])-5} more fields)")

def test_authentication():
    """Test 1: API Authentication"""
    print_section("TEST 1: API 인증 테스트")
    
    try:
        # Authenticate with mock trading
        logger.info("Authenticating with mock trading (vps)...")
        ka.auth(svr='vps', product='01')
        
        trenv = ka.getTREnv()
        logger.info(f"Authentication successful!")
        logger.info(f"Account: {trenv.my_acct}")
        logger.info(f"Product: {trenv.my_prod}")
        
        print(f"✅ 인증 성공")
        print(f"   계좌: {trenv.my_acct}")
        print(f"   상품: {trenv.my_prod}")
        
        return trenv
    except Exception as e:
        logger.error(f"Authentication failed: {e}", exc_info=True)
        print(f"❌ 인증 실패: {e}")
        return None

def test_balance_inquiry(trenv):
    """Test 2: Balance Inquiry"""
    print_section("TEST 2: 잔고 조회 테스트 (해외주식)")
    
    try:
        logger.info("Calling inquire_balance API...")
        logger.info(f"Parameters: cano={trenv.my_acct}, acnt_prdt_cd={trenv.my_prod}, ovrs_excg_cd=NASD, tr_crcy_cd=USD")
        
        df1, df2 = api.inquire_balance(
            cano=trenv.my_acct,
            acnt_prdt_cd=trenv.my_prod,
            ovrs_excg_cd='NASD',
            tr_crcy_cd='USD',
            env_dv='demo'
        )
        
        print("\n📊 Output1 (계좌 정보):")
        log_dataframe(df1, "Output1")
        
        print("\n📊 Output2 (보유 종목):")
        log_dataframe(df2, "Output2")
        
        # Analyze balance data
        if not df1.empty:
            print("\n💰 잔고 분석:")
            for col in df1.columns:
                if 'amt' in col.lower() or 'psbl' in col.lower():
                    value = df1[col].iloc[0]
                    print(f"   {col}: {value}")
                    logger.info(f"Balance field {col}: {value}")
        
        return df1, df2
        
    except Exception as e:
        logger.error(f"Balance inquiry failed: {e}", exc_info=True)
        print(f"❌ 잔고 조회 실패: {e}")
        return None, None

def test_price_inquiry():
    """Test 3: Price Inquiry"""
    print_section("TEST 3: 시세 조회 테스트 (SOXL)")
    
    try:
        logger.info("Calling price API for SOXL...")
        
        df = api.price(
            auth="",
            excd='NASD',
            symb='SOXL',
            env_dv='demo'
        )
        
        log_dataframe(df, "Price Data")
        
        if not df.empty and 'last' in df.columns:
            price = float(df['last'].iloc[0])
            print(f"\n💵 SOXL 현재가: ${price:.2f}")
            logger.info(f"SOXL current price: ${price:.2f}")
            return price
        else:
            print(f"⚠️  가격 정보를 찾을 수 없습니다")
            return None
            
    except Exception as e:
        logger.error(f"Price inquiry failed: {e}", exc_info=True)
        print(f"❌ 시세 조회 실패: {e}")
        return None

def test_order_inquiry(trenv):
    """Test 4: Order History Inquiry"""
    print_section("TEST 4: 주문 내역 조회 테스트")
    
    try:
        logger.info("Calling order history API...")
        
        # Note: This is a placeholder - actual API call depends on available functions
        # Check kis_api.py for available order inquiry functions
        
        print("⚠️  주문 내역 조회 API 확인 필요")
        logger.warning("Order inquiry API needs to be verified in kis_api.py")
        
    except Exception as e:
        logger.error(f"Order inquiry failed: {e}", exc_info=True)
        print(f"❌ 주문 내역 조회 실패: {e}")

def analyze_api_response():
    """Test 5: Analyze API Response Structure"""
    print_section("TEST 5: API 응답 구조 분석")
    
    # Load config to check structure
    config_path = os.path.join(os.path.dirname(__file__), '..', 'kis_devlp.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("\n📋 설정 파일 정보:")
        print(f"   모의투자 App Key: {config.get('paper_app', 'N/A')[:10]}...")
        print(f"   모의투자 계좌: {config.get('my_paper_stock', 'N/A')}")
        print(f"   VPS URL: {config.get('vps', 'N/A')}")
        
        logger.info(f"Config loaded: {config.keys()}")
        
    except Exception as e:
        logger.error(f"Config analysis failed: {e}", exc_info=True)
        print(f"❌ 설정 파일 분석 실패: {e}")

def main():
    """Main diagnostic routine"""
    print("\n" + "="*80)
    print("  🔍 한국투자증권 모의투자 API 진단 스크립트")
    print("="*80)
    print(f"  로그 파일: {log_file}")
    print("="*80)
    
    logger.info("="*80)
    logger.info("Starting KIS Mock Trading API Diagnosis")
    logger.info("="*80)
    
    # Test 1: Authentication
    trenv = test_authentication()
    if not trenv:
        print("\n❌ 인증 실패로 테스트 중단")
        logger.error("Authentication failed - stopping tests")
        return
    
    # Test 2: Balance Inquiry
    df1, df2 = test_balance_inquiry(trenv)
    
    # Test 3: Price Inquiry
    price = test_price_inquiry()
    
    # Test 4: Order Inquiry
    test_order_inquiry(trenv)
    
    # Test 5: API Response Analysis
    analyze_api_response()
    
    # Summary
    print_section("진단 요약")
    
    print("\n✅ 완료된 테스트:")
    print("   1. API 인증")
    print("   2. 잔고 조회")
    print("   3. 시세 조회")
    print("   4. 주문 내역 조회 (확인 필요)")
    print("   5. API 응답 구조 분석")
    
    print(f"\n📝 상세 로그: {log_file}")
    
    # Diagnosis results
    print("\n🔍 진단 결과:")
    
    if df1 is not None and df1.empty:
        print("   ⚠️  잔고 조회 API가 빈 응답 반환 (df1 empty)")
        print("   → 원인: 모의투자 계좌에 자금이 없거나 API 응답 형식 불일치")
        print("   → 조치: 1) 모의투자 계좌 자금 확인")
        print("          2) API 파라미터 검증")
        print("          3) 로그 파일에서 상세 응답 확인")
    
    if price is None:
        print("   ⚠️  시세 조회 실패")
        print("   → 조치: API 엔드포인트 및 파라미터 확인")
    
    logger.info("Diagnosis completed")
    print("\n" + "="*80)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Diagnosis script failed: {e}", exc_info=True)
        print(f"\n❌ 진단 스크립트 오류: {e}")

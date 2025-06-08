"""
CoinBot 공통 유틸리티 함수들
- 시간 처리, 데이터 변환, 수학 계산
- 파일 처리, 문자열 조작, 검증 함수
- 코인 관련 헬퍼 함수들
"""

import os
import re
import json
import math
import hashlib
import decimal
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import time
import random
import string
import logging

# ==========================================
# 시간 관련 유틸리티
# ==========================================

def get_kst_now() -> datetime:
    """한국 시간 현재 시각 반환"""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Seoul"))

def get_utc_now() -> datetime:
    """UTC 현재 시각 반환"""
    return datetime.now(timezone.utc)

def kst_to_utc(kst_time: datetime) -> datetime:
    """KST 시간을 UTC로 변환"""
    from zoneinfo import ZoneInfo
    if kst_time.tzinfo is None:
        kst_time = kst_time.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return kst_time.astimezone(timezone.utc)

def utc_to_kst(utc_time: datetime) -> datetime:
    """UTC 시간을 KST로 변환"""
    from zoneinfo import ZoneInfo
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    return utc_time.astimezone(ZoneInfo("Asia/Seoul"))

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """datetime을 포맷된 문자열로 변환"""
    return dt.strftime(format_str)

def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """문자열을 datetime으로 변환"""
    return datetime.strptime(dt_str, format_str)

def get_time_ago(minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    """현재 시간에서 지정된 시간 전 반환"""
    return get_kst_now() - timedelta(minutes=minutes, hours=hours, days=days)

def get_time_after(minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    """현재 시간에서 지정된 시간 후 반환"""
    return get_kst_now() + timedelta(minutes=minutes, hours=hours, days=days)

def seconds_to_readable(seconds: int) -> str:
    """초를 읽기 쉬운 형태로 변환"""
    if seconds < 60:
        return f"{seconds}초"
    elif seconds < 3600:
        return f"{seconds // 60}분 {seconds % 60}초"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}시간 {minutes}분"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}일 {hours}시간"

def is_market_open() -> bool:
    """암호화폐 시장은 24/7이므로 항상 True"""
    return True

def get_trading_session() -> str:
    """현재 거래 세션 반환 (아시아/유럽/미국)"""
    kst_hour = get_kst_now().hour
    
    if 0 <= kst_hour < 8:
        return "미국_연장"
    elif 8 <= kst_hour < 16:
        return "아시아"
    elif 16 <= kst_hour < 24:
        return "유럽_미국"
    else:
        return "글로벌"

# ==========================================
# 숫자 및 계산 유틸리티
# ==========================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """안전한 float 변환"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """안전한 int 변환"""
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default

def round_down(value: float, decimals: int = 0) -> float:
    """내림 반올림"""
    multiplier = 10 ** decimals
    return math.floor(value * multiplier) / multiplier

def round_up(value: float, decimals: int = 0) -> float:
    """올림 반올림"""
    multiplier = 10 ** decimals
    return math.ceil(value * multiplier) / multiplier

def format_number(num: float, decimals: int = 2, use_comma: bool = True) -> str:
    """숫자를 포맷된 문자열로 변환"""
    if use_comma:
        return f"{num:,.{decimals}f}"
    else:
        return f"{num:.{decimals}f}"

def format_currency(amount: float, currency: str = "KRW") -> str:
    """통화 형태로 포맷"""
    if currency == "KRW":
        return f"₩{amount:,.0f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "BTC":
        return f"₿{amount:.8f}"
    else:
        return f"{amount:.4f} {currency}"

def format_percentage(ratio: float, decimals: int = 2) -> str:
    """비율을 퍼센트로 포맷"""
    return f"{ratio * 100:+.{decimals}f}%"

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """변화율 계산"""
    if old_value == 0:
        return 0.0
    return (new_value - old_value) / old_value

def clamp(value: float, min_val: float, max_val: float) -> float:
    """값을 범위 내로 제한"""
    return max(min_val, min(value, max_val))

def normalize(value: float, min_val: float, max_val: float) -> float:
    """값을 0-1 범위로 정규화"""
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)

def calculate_compound_return(initial: float, final: float, periods: int) -> float:
    """복리 수익률 계산"""
    if initial <= 0 or periods <= 0:
        return 0.0
    return (final / initial) ** (1 / periods) - 1

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """샤프 비율 계산"""
    if not returns or len(returns) < 2:
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    if std_return == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_return

def calculate_max_drawdown(values: List[float]) -> float:
    """최대 낙폭 계산"""
    if not values:
        return 0.0
    
    peak = values[0]
    max_dd = 0.0
    
    for value in values:
        if value > peak:
            peak = value
        else:
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
    
    return max_dd

# ==========================================
# 코인 관련 유틸리티
# ==========================================

def parse_ticker(ticker: str) -> Tuple[str, str]:
    """티커에서 기준통화와 거래통화 분리"""
    # KRW-BTC -> ('KRW', 'BTC')
    parts = ticker.split('-')
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return 'KRW', ticker

def get_coin_name(ticker: str) -> str:
    """티커에서 코인명만 추출"""
    _, coin = parse_ticker(ticker)
    return coin

def format_ticker(base: str, quote: str) -> str:
    """기준통화와 거래통화로 티커 생성"""
    return f"{base}-{quote}"

def is_krw_market(ticker: str) -> bool:
    """KRW 마켓 여부 확인"""
    base, _ = parse_ticker(ticker)
    return base == 'KRW'

def calculate_krw_value(price: float, quantity: float, ticker: str = None) -> float:
    """KRW 가치 계산"""
    if ticker and not is_krw_market(ticker):
        # BTC 마켓 등의 경우 별도 변환 로직 필요
        return price * quantity  # 임시 처리
    return price * quantity

def get_minimum_order_amount(ticker: str) -> int:
    """최소 주문 금액 반환 (업비트 기준)"""
    if is_krw_market(ticker):
        return 5000  # KRW 마켓 최소 주문금액
    else:
        return 10000  # 기타 마켓

def calculate_commission(amount: float, rate: float = 0.0005) -> float:
    """수수료 계산 (업비트 기준 0.05%)"""
    return amount * rate

def adjust_quantity_precision(quantity: float, ticker: str) -> float:
    """수량 정밀도 조정"""
    # 대부분의 코인은 소수점 8자리까지
    return round(quantity, 8)

def adjust_price_precision(price: float, ticker: str) -> float:
    """가격 정밀도 조정"""
    coin = get_coin_name(ticker)
    
    # 코인별 가격 단위 조정 (업비트 기준)
    if coin in ['BTC', 'ETH']:
        if price >= 1000000:
            return round(price, 0)
        elif price >= 100000:
            return round(price, 0)
        else:
            return round(price, 1)
    else:
        # 기타 코인들
        if price >= 1000:
            return round(price, 0)
        elif price >= 100:
            return round(price, 1)
        elif price >= 10:
            return round(price, 2)
        else:
            return round(price, 4)

# ==========================================
# 데이터 처리 유틸리티
# ==========================================

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """딕셔너리에서 안전하게 값 가져오기"""
    try:
        return data.get(key, default) if isinstance(data, dict) else default
    except:
        return default

def safe_get_nested(data: Dict, keys: List[str], default: Any = None) -> Any:
    """중첩된 딕셔너리에서 안전하게 값 가져오기"""
    try:
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    except:
        return default

def merge_dicts(*dicts: Dict) -> Dict:
    """여러 딕셔너리 병합"""
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def filter_dict(data: Dict, allowed_keys: List[str]) -> Dict:
    """허용된 키만 포함한 딕셔너리 반환"""
    return {k: v for k, v in data.items() if k in allowed_keys}

def remove_none_values(data: Dict) -> Dict:
    """None 값 제거"""
    return {k: v for k, v in data.items() if v is not None}

def flatten_dict(data: Dict, separator: str = '.') -> Dict:
    """중첩된 딕셔너리를 평면화"""
    result = {}
    
    def _flatten(obj: Dict, prefix: str = ''):
        for key, value in obj.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key
            if isinstance(value, dict):
                _flatten(value, new_key)
            else:
                result[new_key] = value
    
    _flatten(data)
    return result

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """리스트를 청크 단위로 분할"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def remove_duplicates(lst: List, key: Optional[str] = None) -> List:
    """중복 제거"""
    if key is None:
        return list(dict.fromkeys(lst))
    else:
        seen = set()
        result = []
        for item in lst:
            item_key = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if item_key not in seen:
                seen.add(item_key)
                result.append(item)
        return result
    # ==========================================
# 파일 및 디렉토리 유틸리티
# ==========================================

def ensure_dir(path: Union[str, Path]) -> Path:
    """디렉토리 존재 확인 및 생성"""
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

def safe_file_write(filepath: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
    """안전한 파일 쓰기"""
    try:
        filepath = Path(filepath)
        ensure_dir(filepath.parent)
        
        # 임시 파일에 먼저 쓰기
        temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
        with open(temp_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # 원자적 이동
        temp_path.replace(filepath)
        return True
    except Exception as e:
        logging.error(f"파일 쓰기 실패 {filepath}: {e}")
        return False

def safe_file_read(filepath: Union[str, Path], encoding: str = 'utf-8', default: str = '') -> str:
    """안전한 파일 읽기"""
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logging.error(f"파일 읽기 실패 {filepath}: {e}")
        return default

def safe_json_save(filepath: Union[str, Path], data: Any) -> bool:
    """안전한 JSON 저장"""
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        return safe_file_write(filepath, json_str)
    except Exception as e:
        logging.error(f"JSON 저장 실패 {filepath}: {e}")
        return False

def safe_json_load(filepath: Union[str, Path], default: Any = None) -> Any:
    """안전한 JSON 로드"""
    try:
        content = safe_file_read(filepath)
        return json.loads(content) if content else default
    except Exception as e:
        logging.error(f"JSON 로드 실패 {filepath}: {e}")
        return default

def get_file_size(filepath: Union[str, Path]) -> int:
    """파일 크기 반환 (바이트)"""
    try:
        return Path(filepath).stat().st_size
    except:
        return 0

def get_file_age(filepath: Union[str, Path]) -> timedelta:
    """파일 나이 반환"""
    try:
        mtime = Path(filepath).stat().st_mtime
        return datetime.now() - datetime.fromtimestamp(mtime)
    except:
        return timedelta(days=999)

def cleanup_old_files(directory: Union[str, Path], max_age_days: int = 30, pattern: str = "*") -> int:
    """오래된 파일들 정리"""
    try:
        directory = Path(directory)
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        for filepath in directory.glob(pattern):
            if filepath.is_file():
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                if mtime < cutoff_time:
                    filepath.unlink()
                    deleted_count += 1
        
        return deleted_count
    except Exception as e:
        logging.error(f"파일 정리 실패: {e}")
        return 0

def rotate_file(filepath: Union[str, Path], max_backups: int = 5) -> bool:
    """파일 로테이션"""
    try:
        filepath = Path(filepath)
        
        if not filepath.exists():
            return True
        
        # 기존 백업 파일들 이동
        for i in range(max_backups - 1, 0, -1):
            old_backup = filepath.with_suffix(f"{filepath.suffix}.{i}")
            new_backup = filepath.with_suffix(f"{filepath.suffix}.{i + 1}")
            
            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)
        
        # 현재 파일을 .1로 이동
        backup_path = filepath.with_suffix(f"{filepath.suffix}.1")
        if backup_path.exists():
            backup_path.unlink()
        filepath.rename(backup_path)
        
        return True
    except Exception as e:
        logging.error(f"파일 로테이션 실패: {e}")
        return False

def get_disk_usage(path: Union[str, Path]) -> Dict[str, int]:
    """디스크 사용량 정보"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent': (used / total) * 100
        }
    except:
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}

# ==========================================
# 문자열 처리 유틸리티
# ==========================================

def clean_string(text: str) -> str:
    """문자열 정리 (공백, 특수문자 제거)"""
    if not isinstance(text, str):
        return str(text)
    
    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    return text.strip()

def sanitize_filename(filename: str) -> str:
    """파일명에 사용할 수 없는 문자 제거"""
    # Windows/Unix에서 사용할 수 없는 문자들 제거
    invalid_chars = r'[<>:"/\\|?*]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # 연속된 언더스코어를 하나로
    filename = re.sub(r'_+', '_', filename)
    
    # 앞뒤 점과 공백 제거
    filename = filename.strip('. ')
    
    return filename or 'untitled'

def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """문자열 자르기"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_numbers(text: str) -> List[float]:
    """문자열에서 숫자 추출"""
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]

def mask_sensitive_info(text: str, mask_char: str = '*') -> str:
    """민감한 정보 마스킹"""
    # API 키 마스킹 (앞뒤 4자리만 보이게)
    text = re.sub(r'([A-Za-z0-9]{4})[A-Za-z0-9]+([A-Za-z0-9]{4})', 
                  rf'\1{mask_char * 8}\2', text)
    
    # 이메일 마스킹
    text = re.sub(r'([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', 
                  rf'{mask_char * 5}@\2', text)
    
    return text

def generate_random_string(length: int = 8, include_numbers: bool = True, 
                          include_symbols: bool = False) -> str:
    """랜덤 문자열 생성"""
    chars = string.ascii_letters
    
    if include_numbers:
        chars += string.digits
    
    if include_symbols:
        chars += '!@#$%^&*'
    
    return ''.join(random.choice(chars) for _ in range(length))

def camel_to_snake(name: str) -> str:
    """camelCase를 snake_case로 변환"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def snake_to_camel(name: str) -> str:
    """snake_case를 camelCase로 변환"""
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

# ==========================================
# 해시 및 보안 유틸리티
# ==========================================

def generate_hash(data: str, algorithm: str = 'sha256') -> str:
    """데이터 해시 생성"""
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(data.encode('utf-8'))
    return hash_func.hexdigest()

def generate_uuid() -> str:
    """UUID 생성"""
    import uuid
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """짧은 ID 생성"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def verify_hash(data: str, expected_hash: str, algorithm: str = 'sha256') -> bool:
    """해시 검증"""
    actual_hash = generate_hash(data, algorithm)
    return actual_hash == expected_hash

def obfuscate_string(text: str, key: str = 'coinbot') -> str:
    """간단한 문자열 난독화"""
    result = []
    key_len = len(key)
    
    for i, char in enumerate(text):
        key_char = key[i % key_len]
        obfuscated_char = chr(ord(char) ^ ord(key_char))
        result.append(obfuscated_char)
    
    return ''.join(result)

def deobfuscate_string(obfuscated_text: str, key: str = 'coinbot') -> str:
    """난독화된 문자열 복원"""
    return obfuscate_string(obfuscated_text, key)  # XOR는 자기 역함수

# ==========================================
# 검증 및 체크 유틸리티
# ==========================================

def is_valid_email(email: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_phone(phone: str) -> bool:
    """전화번호 형식 검증 (한국)"""
    pattern = r'^(010|011|016|017|018|019)-?\d{3,4}-?\d{4}$'
    return bool(re.match(pattern, phone.replace('-', '')))

def is_valid_url(url: str) -> bool:
    """URL 형식 검증"""
    pattern = r'^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))

def is_numeric(value: Any) -> bool:
    """숫자 여부 확인"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def is_positive_number(value: Any) -> bool:
    """양수 여부 확인"""
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False

def validate_ticker(ticker: str) -> bool:
    """티커 형식 검증"""
    pattern = r'^[A-Z]{3,}-[A-Z]{2,}$'
    return bool(re.match(pattern, ticker))

def validate_price(price: Any) -> bool:
    """가격 유효성 검증"""
    try:
        price_float = float(price)
        return price_float > 0 and price_float < 1e15  # 현실적인 범위
    except (ValueError, TypeError):
        return False

def validate_quantity(quantity: Any) -> bool:
    """수량 유효성 검증"""
    try:
        qty_float = float(quantity)
        return qty_float > 0 and qty_float < 1e12  # 현실적인 범위
    except (ValueError, TypeError):
        return False

# ==========================================
# 성능 및 디버깅 유틸리티
# ==========================================

def timing_decorator(func):
    """함수 실행 시간 측정 데코레이터"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logging.debug(f"{func.__name__} 실행 시간: {execution_time:.4f}초")
        
        return result
    return wrapper

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      backoff_factor: float = 2.0, exceptions: Tuple = (Exception,)):
    """예외 발생시 재시도 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    logging.warning(f"{func.__name__} 실패 (시도 {retries}/{max_retries}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            return None
        return wrapper
    return decorator

def memory_usage():
    """메모리 사용량 확인"""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss,  # 물리 메모리
        'vms': memory_info.vms,  # 가상 메모리
        'percent': process.memory_percent(),
        'rss_mb': memory_info.rss / 1024 / 1024,
        'vms_mb': memory_info.vms / 1024 / 1024
    }

def cpu_usage():
    """CPU 사용량 확인"""
    import psutil
    return {
        'percent': psutil.cpu_percent(interval=1),
        'count': psutil.cpu_count(),
        'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
    }

def system_health_check() -> Dict[str, Any]:
    """시스템 상태 종합 체크"""
    try:
        import psutil
        
        # CPU 정보
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        
        # 네트워크 정보
        network = psutil.net_io_counters()
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count()
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            'timestamp': get_kst_now().isoformat()
        }
    except Exception as e:
        logging.error(f"시스템 상태 체크 실패: {e}")
        return {'error': str(e)}

# ==========================================
# 설정 및 환경 유틸리티
# ==========================================

def load_env_file(env_path: Union[str, Path] = '.env') -> Dict[str, str]:
    """환경변수 파일 로드"""
    env_vars = {}
    env_path = Path(env_path)
    
    if not env_path.exists():
        return env_vars
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    env_vars[key] = value
        
        return env_vars
    except Exception as e:
        logging.error(f"환경변수 파일 로드 실패: {e}")
        return {}

def get_env_var(key: str, default: Any = None, var_type: type = str) -> Any:
    """환경변수 안전하게 가져오기"""
    value = os.getenv(key, default)
    
    if value is None:
        return default
    
    try:
        if var_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        elif var_type == list:
            return [item.strip() for item in value.split(',')]
        else:
            return var_type(value)
    except (ValueError, TypeError):
        return default

def check_required_env_vars(required_vars: List[str]) -> List[str]:
    """필수 환경변수 체크"""
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    return missing_vars

def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    current_path = Path(__file__).resolve()
    
    # config, core, utils 등이 있는 디렉토리를 찾기
    for parent in current_path.parents:
        if (parent / 'config').exists() and (parent / 'core').exists():
            return parent
    
    # 찾지 못하면 현재 파일의 2단계 상위
    return current_path.parent.parent

# ==========================================
# 암호화폐 특화 유틸리티
# ==========================================

def normalize_ticker_list(tickers: List[str]) -> List[str]:
    """티커 리스트 정규화"""
    normalized = []
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if not ticker.startswith('KRW-'):
            ticker = f'KRW-{ticker}'
        normalized.append(ticker)
    return list(set(normalized))  # 중복 제거

def get_major_coins() -> List[str]:
    """주요 코인 목록 반환"""
    return [
        'KRW-BTC', 'KRW-ETH', 'KRW-ADA', 'KRW-DOT',
        'KRW-LINK', 'KRW-SOL', 'KRW-MATIC', 'KRW-ATOM',
        'KRW-AVAX', 'KRW-NEAR', 'KRW-ALGO', 'KRW-XRP'
    ]

def categorize_coins(tickers: List[str]) -> Dict[str, List[str]]:
    """코인들을 카테고리별로 분류"""
    categories = {
        'major': [],      # 주요 코인 (시가총액 상위)
        'defi': [],       # DeFi 관련
        'layer1': [],     # 레이어1 블록체인
        'meme': [],       # 밈 코인
        'others': []      # 기타
    }
    
    # 간단한 분류 (실제로는 더 정교한 분류 필요)
    major_coins = ['BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'AVAX']
    defi_coins = ['UNI', 'SUSHI', 'COMP', 'AAVE', 'MKR']
    layer1_coins = ['BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'AVAX', 'ATOM', 'NEAR']
    meme_coins = ['DOGE', 'SHIB']
    
    for ticker in tickers:
        coin = get_coin_name(ticker)
        
        if coin in major_coins:
            categories['major'].append(ticker)
        elif coin in defi_coins:
            categories['defi'].append(ticker)
        elif coin in layer1_coins and ticker not in categories['major']:
            categories['layer1'].append(ticker)
        elif coin in meme_coins:
            categories['meme'].append(ticker)
        else:
            categories['others'].append(ticker)
    
    return categories

def calculate_portfolio_metrics(positions: List[Dict]) -> Dict[str, Any]:
    """포트폴리오 지표 계산"""
    if not positions:
        return {}
    
    total_value = sum(pos.get('current_value', 0) for pos in positions)
    total_invested = sum(pos.get('total_invested', 0) for pos in positions)
    
    if total_invested == 0:
        return {}
    
    # 개별 수익률
    returns = []
    weights = []
    
    for pos in positions:
        if pos.get('total_invested', 0) > 0:
            pnl_ratio = (pos.get('current_value', 0) - pos.get('total_invested', 0)) / pos.get('total_invested', 1)
            weight = pos.get('total_invested', 0) / total_invested
            
            returns.append(pnl_ratio)
            weights.append(weight)
    
    if not returns:
        return {}
    
    # 가중평균 수익률
    weighted_return = sum(r * w for r, w in zip(returns, weights))
    
    # 포트폴리오 분산
    portfolio_variance = sum(w * (r - weighted_return) ** 2 for r, w in zip(returns, weights))
    portfolio_std = math.sqrt(portfolio_variance)
    
    return {
        'total_value': total_value,
        'total_invested': total_invested,
        'total_pnl': total_value - total_invested,
        'total_return': (total_value - total_invested) / total_invested,
        'weighted_return': weighted_return,
        'portfolio_std': portfolio_std,
        'position_count': len(positions),
        'diversification_ratio': len(set(pos.get('ticker') for pos in positions)) / len(positions)
    }

# ==========================================
# 알림 및 메시지 유틸리티
# ==========================================

def format_trade_message(action: str, ticker: str, price: float, 
                         quantity: float, amount: float, **kwargs) -> str:
    """거래 메시지 포맷"""
    emoji = "💰" if action == "BUY" else "💸"
    coin = get_coin_name(ticker)
    
    message = f"""{emoji} **{action} 거래**

🪙 **코인**: {coin}
💵 **가격**: {format_currency(price)}
📊 **수량**: {quantity:.6f}
💰 **금액**: {format_currency(amount)}
⏰ **시간**: {format_datetime(get_kst_now(), '%H:%M:%S')}"""

    # 추가 정보
    if 'strategy' in kwargs:
        message += f"\n🎯 **전략**: {kwargs['strategy']}"
    
    if 'confidence' in kwargs:
        message += f"\n📈 **신뢰도**: {kwargs['confidence']:.1%}"
    
    if 'profit_ratio' in kwargs and kwargs['profit_ratio'] is not None:
        emoji = "📈" if kwargs['profit_ratio'] >= 0 else "📉"
        message += f"\n{emoji} **수익률**: {format_percentage(kwargs['profit_ratio'])}"
    
    return message

def format_portfolio_message(portfolio_data: Dict) -> str:
    """포트폴리오 메시지 포맷"""
    total_value = portfolio_data.get('total_value', 0)
    total_return = portfolio_data.get('total_return', 0)
    positions_count = portfolio_data.get('total_positions', 0)
    
    emoji = "📈" if total_return >= 0 else "📉"
    
    message = f"""{emoji} **포트폴리오 현황**

💰 **총 자산**: {format_currency(total_value)}
📊 **수익률**: {format_percentage(total_return)}
💼 **보유 종목**: {positions_count}개
⏰ **업데이트**: {format_datetime(get_kst_now(), '%m-%d %H:%M')}"""
    
    return message

def format_alert_message(alert_type: str, title: str, description: str, 
                        severity: str = "INFO") -> str:
    """알림 메시지 포맷"""
    emoji_map = {
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'SUCCESS': '✅',
        'CRITICAL': '🚨'
    }
    
    emoji = emoji_map.get(severity, 'ℹ️')
    
    message = f"""{emoji} **{alert_type}**

**{title}**

{description}

⏰ {format_datetime(get_kst_now())}"""
    
    return message

# ==========================================
# 에러 처리 및 로깅 유틸리티
# ==========================================

def setup_logging(log_level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger('coinbot')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 핸들러가 이미 있으면 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택사항)
    if log_file:
        ensure_dir(Path(log_file).parent)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def exception_handler(func):
    """예외 처리 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger('coinbot')
            logger.error(f"{func.__name__} 실행 중 오류: {e}", exc_info=True)
            return None
    return wrapper

def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('coinbot')
        logger.debug(f"{func.__name__} 호출: args={args}, kwargs={kwargs}")
        
        result = func(*args, **kwargs)
        
        logger.debug(f"{func.__name__} 완료: result={result}")
        return result
    return wrapper

# ==========================================
# 전역 유틸리티 함수들
# ==========================================

def get_app_version() -> str:
    """앱 버전 반환"""
    try:
        version_file = get_project_root() / 'VERSION'
        if version_file.exists():
            return safe_file_read(version_file).strip()
        else:
            return '1.0.0'
    except:
        return '1.0.0'

def get_build_info() -> Dict[str, str]:
    """빌드 정보 반환"""
    return {
        'version': get_app_version(),
        'build_time': format_datetime(get_kst_now()),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'platform': os.name,
        'project_root': str(get_project_root())
    }

# 모듈 import 시 필요한 초기화
if __name__ != "__main__":
    # 기본 로거 설정
    import sys
    setup_logging()    
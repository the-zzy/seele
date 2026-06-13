"""
东方财富 F10 公司概况抓取服务
"""

import json
import logging
import urllib.request
from typing import Optional

from app import schemas

logger = logging.getLogger(__name__)

SURVEY_API_URL = 'http://f10.eastmoney.com/CompanySurvey/CompanySurveyAjax?code={code}'


def _infer_market_prefix(symbol: str) -> str:
    """根据股票代码推断交易所前缀"""
    if symbol.startswith('6'):
        return 'SH'
    if symbol.startswith(('82', '83', '87', '88', '89', '92', '93')):
        return 'BJ'
    if symbol.startswith(('4', '8')):
        return 'BJ'
    return 'SZ'


def fetch_company_survey(symbol: str) -> Optional[schemas.StockCompanyProfileCreate]:
    """从东方财富 F10 抓取单只股票的公司概况

    Returns:
        StockCompanyProfileCreate 对象，抓取失败返回 None
    """
    prefix = _infer_market_prefix(symbol)
    url = SURVEY_API_URL.format(code=f'{prefix}{symbol}')

    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ),
                'Referer': 'http://f10.eastmoney.com/',
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
    except Exception as exc:
        logger.warning('[COMPANY_SURVEY] 请求失败 %s: %s', symbol, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning('[COMPANY_SURVEY] JSON 解析失败 %s: %s', symbol, exc)
        return None

    jbzl = data.get('jbzl') or {}
    fxxg = data.get('fxxg') or {}

    # 关键字段校验：如果连公司全称都没有，认为数据无效
    if not jbzl.get('gsmc'):
        logger.warning('[COMPANY_SURVEY] 数据缺失 %s: gsmc 为空', symbol)
        return None

    # 清理文本：去除公司简介、经营范围的多余空白
    company_profile = jbzl.get('gsjj', '')
    business_scope = jbzl.get('jyfw', '')
    if company_profile:
        company_profile = ' '.join(company_profile.split())
    if business_scope:
        business_scope = ' '.join(business_scope.split())

    return schemas.StockCompanyProfileCreate(
        symbol=symbol,
        company_full_name=jbzl.get('gsmc'),
        english_name=jbzl.get('ywmc'),
        chairman=jbzl.get('dsz'),
        general_manager=jbzl.get('zjl'),
        secretary=jbzl.get('dm'),
        legal_representative=jbzl.get('frdb'),
        phone=jbzl.get('lxdh'),
        email=jbzl.get('dzxx'),
        fax=jbzl.get('cz'),
        website=jbzl.get('gswz'),
        office_address=jbzl.get('bgdz'),
        reg_address=jbzl.get('zcdz'),
        postcode=jbzl.get('yzbm'),
        reg_capital=jbzl.get('zczb'),
        employees=_parse_int(jbzl.get('gyrs')),
        founded_date=fxxg.get('clrq'),
        company_profile=company_profile or None,
        business_scope=business_scope or None,
        industry_detail=jbzl.get('sszjhhy'),
        exchange=jbzl.get('ssjys'),
    )


def _parse_int(val) -> Optional[int]:
    """安全解析整数"""
    if val is None:
        return None
    try:
        s = str(val).replace(',', '').strip()
        return int(s)
    except (ValueError, TypeError):
        return None

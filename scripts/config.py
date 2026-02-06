"""
Configuration utilities for loading keywords and settings
"""
import yaml
import os

def load_keywords(mode='weekly', access_level='internal'):
    """
    키워드 로딩 함수
    
    Args:
        mode: 'weekly' or 'daily'
        access_level: 'internal' or 'external'
    
    Returns:
        List of keywords
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'keywords.yaml')
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    keywords = []
    
    if mode == 'weekly':
        # Weekly 모드: 모든 카테고리 키워드 통합
        for category in ['distribution', 'bd', 'approval', 'reimbursement', 'zuellig', 
                        'client', 'therapeutic', 'supply']:
            keywords.extend(config.get(category, []))
        
        # Internal이면 경쟁사 제품도 추가
        if access_level == 'internal':
            keywords.extend(config.get('competitor', []))
    
    elif mode == 'daily':
        # Daily 모드: Daily 전용 키워드만
        keywords = config.get('daily', [])
    
    return keywords

def get_excluded_keywords(access_level='external'):
    """
    External용 제외 키워드 가져오기
    
    Args:
        access_level: 'internal' or 'external'
    
    Returns:
        List of keywords to exclude
    """
    if access_level == 'internal':
        return []  # Internal은 제외할 것 없음
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'keywords.yaml')
    with open(config_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    excluded = []
    external_exclude = config.get('external_exclude', {})
    
    # 모든 제외 카테고리의 키워드 통합
    for category in ['distribution_competitors', 'competitor_products']:
        excluded.extend(external_exclude.get(category, []))
    
    return excluded

def should_exclude_article(article, excluded_keywords):
    """
    기사가 제외 키워드를 포함하는지 확인
    
    Args:
        article: 기사 dict (title, summary 포함)
        excluded_keywords: 제외할 키워드 리스트
    
    Returns:
        Boolean - True면 제외해야 함
    """
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    
    for keyword in excluded_keywords:
        if keyword.lower() in text:
            return True
    
    return False

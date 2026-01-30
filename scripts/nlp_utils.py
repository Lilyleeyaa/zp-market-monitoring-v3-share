"""
NLP Utilities for Smart Search
Provides Korean morphological analysis, keyword expansion, and semantic similarity
"""
import re
from typing import List, Set, Tuple
import numpy as np

# Try to import KoNLPy, fallback to basic tokenization if not available
try:
    from konlpy.tag import Okt
    HAS_KONLPY = True
    okt = Okt()
except ImportError:
    HAS_KONLPY = False
    print("[Warning] KoNLPy not installed. Using basic tokenization.")
    print("Install with: pip install konlpy")

from sentence_transformers import SentenceTransformer

# Global sentence transformer for embeddings
_st_model = None

def get_sentence_transformer():
    """Lazy load sentence transformer model"""
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _st_model


def extract_morphemes(text: str) -> List[str]:
    """
    Extract Korean morphemes from text
    
    Args:
        text: Input Korean text
        
    Returns:
        List of morphemes (nouns, verbs, adjectives)
    """
    if not text:
        return []
    
    if HAS_KONLPY:
        # Use KoNLPy for accurate morphological analysis
        morphs = okt.morphs(text, stem=True)  # stem=True for normalization
        # Filter out stopwords and single characters
        morphs = [m for m in morphs if len(m) > 1]
        return morphs
    else:
        # Fallback: simple space split
        words = re.sub(r'[^가-힣a-zA-Z0-9\\s]', '', text).split()
        return [w for w in words if len(w) > 1]


def expand_keyword(keyword: str) -> Set[str]:
    """
    Expand keyword into morphemes for broader search
    
    Args:
        keyword: Original search keyword (e.g., "의약품유통")
        
    Returns:
        Set of expanded terms including morphemes
    """
    expanded = {keyword}  # Always include original
    
    # Extract morphemes
    morphemes = extract_morphemes(keyword)
    expanded.update(morphemes)
    
    # Manual synonym expansion (domain-specific)
    synonym_map = {
        "의약품": ["약품", "의약"],
        "유통": ["배송", "공급", "판매"],
        "신약": ["신제품", "새약"],
        "허가": ["승인", "인가"],
        "급여": ["보험", "보험급여"],
    }
    
    for morph in morphemes:
        if morph in synonym_map:
            expanded.update(synonym_map[morph])
    
    return expanded


def calculate_relevance_score(article_text: str, query_keywords: List[str]) -> float:
    """
    Calculate relevance score between article and query keywords
    Uses simple keyword frequency and position weighting
    
    Args:
        article_text: Article title + summary
        query_keywords: List of query keywords/morphemes
        
    Returns:
        Relevance score (0.0 to 1.0)
    """
    if not article_text or not query_keywords:
        return 0.0
    
    article_lower = article_text.lower()
    score = 0.0
    
    for keyword in query_keywords:
        keyword_lower = keyword.lower()
        # Count occurrences
        count = article_lower.count(keyword_lower)
        if count > 0:
            # Base score from frequency (diminishing returns)
            freq_score = min(count / 3.0, 1.0)  # Cap at 1.0
            score += freq_score
    
    # Normalize by number of keywords
    if query_keywords:
        score = score / len(query_keywords)
    
    return min(score, 1.0)


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity using sentence embeddings
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Cosine similarity (0.0 to 1.0)
    """
    if not text1 or not text2:
        return 0.0
    
    model = get_sentence_transformer()
    
    # Generate embeddings
    emb1 = model.encode(text1)
    emb2 = model.encode(text2)
    
    # Cosine similarity
    cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    return float(cos_sim)


def is_semantic_duplicate(new_article: str, existing_articles: List[str], threshold: float = 0.85) -> bool:
    """
    Check if new article is semantically similar to existing articles
    
    Args:
        new_article: New article text (title + summary)
        existing_articles: List of existing article texts
        threshold: Similarity threshold (default 0.85)
        
    Returns:
        True if duplicate found
    """
    for existing in existing_articles:
        sim = semantic_similarity(new_article, existing)
        if sim >= threshold:
            return True
    return False


def tokenize_korean(text: str) -> List[str]:
    """
    Simple Korean-aware tokenization
    
    Args:
        text: Input text
        
    Returns:
        List of tokens
    """
    if HAS_KONLPY:
        return okt.morphs(text)
    else:
        # Fallback
        return re.sub(r'[^가-힣a-zA-Z0-9\\s]', '', text).split()


# Test function
if __name__ == "__main__":
    print("="*70)
    print("NLP Utilities Test")
    print("="*70)
    
    # Test morpheme extraction
    test_text = "의약품유통"
    print(f"\n1. Morpheme extraction: '{test_text}'")
    morphs = extract_morphemes(test_text)
    print(f"   Result: {morphs}")
    
    # Test keyword expansion
    print(f"\n2. Keyword expansion: '{test_text}'")
    expanded = expand_keyword(test_text)
    print(f"   Expanded: {expanded}")
    
    # Test relevance scoring
    article = "의약품 유통 시장이 빠르게 성장하고 있다"
    print(f"\n3. Relevance score")
    print(f"   Article: '{article}'")
    print(f"   Keywords: {list(expanded)}")
    score = calculate_relevance_score(article, list(expanded))
    print(f"   Score: {score:.3f}")
    
    # Test semantic similarity
    text1 = "삼성바이오로직스 실적 급등"
    text2 = "삼성바이오 매출 크게 증가"
    print(f"\n4. Semantic similarity")
    print(f"   Text1: '{text1}'")
    print(f"   Text2: '{text2}'")
    sim = semantic_similarity(text1, text2)
    print(f"   Similarity: {sim:.3f}")
    
    print("\n" + "="*70)

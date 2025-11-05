from typing import List, Dict, Any, Set, Tuple
from itertools import combinations
import os

from models.user_story import UserStory

# NLTK and lemmatization/similarity utilities
try:
    import nltk
    from nltk.corpus import wordnet as wn
    from nltk.stem import WordNetLemmatizer
    _wnl = WordNetLemmatizer()
    # Ensure wordnet is available (lazy safe-guard)
    try:
        wn.synsets("dog")
    except LookupError:
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)
except Exception:  # If nltk unavailable at runtime, degrade gracefully
    nltk = None
    wn = None
    _wnl = None

# Optional: word2vec via gensim if available and a model path is provided in env WORD2VEC_PATH
try:
    from gensim.models import KeyedVectors  # type: ignore
    import gensim.downloader as api  # type: ignore
    _w2v_model = None

    def _load_w2v_model():
        """Load a Word2Vec model lazily.

        Priority:
        1) WORD2VEC_PATH (custom trained or downloaded file)
        2) gensim.downloader 'word2vec-google-news-300' (pretrained)
        """
        global _w2v_model
        if _w2v_model is not None:
            return _w2v_model
        # 1) Custom path
        path = os.environ.get('WORD2VEC_PATH')
        if path and os.path.exists(path):
            try:
                _w2v_model = KeyedVectors.load(path, mmap='r')
                return _w2v_model
            except Exception:
                try:
                    _w2v_model = KeyedVectors.load_word2vec_format(path, binary=True)
                    return _w2v_model
                except Exception:
                    _w2v_model = None
        # 2) Pretrained GoogleNews (will download if not present in gensim-data)
        try:
            _w2v_model = api.load('word2vec-google-news-300')
        except Exception:
            _w2v_model = None
        return _w2v_model
except Exception:
    KeyedVectors = None  # type: ignore
    _w2v_model = None

    def _load_w2v_model():
        return None


def generate_synonym_records(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate WordNet-based synonyms for each concept (fallback to identity)."""
    records = []
    for c in concepts:
        name = (c.get('name') or c.get('text')) if isinstance(c, dict) else str(c)
        if not name:
            continue
        syns: Set[str] = set([name])
        if wn is not None:
            try:
                for pos in (wn.NOUN, wn.VERB):
                    for s in wn.synsets(name, pos=pos):
                        for l in s.lemmas():
                            syns.add(l.name().replace('_', ' '))
            except Exception:
                pass
        records.append({'concept': name, 'synonyms': sorted(syns)})
    return records


def save_synonyms(session, user_story_id: int, synonym_records: List[Dict[str, Any]]):
    """Deprecated: Concept-based synonym persistence removed in simplified model."""
    return


def save_svo_relationships(session, svo_list: List[Dict[str, Any]]):
    """Deprecated: no persistence to concept_map in simplified model."""
    return


# ---- Normalization, Similarity, and Pair-wise helpers ----

def _lemmatize(term: str, is_verb: bool) -> str:
    if not term:
        return term
    t = term.strip().lower()
    if _wnl is None:
        return t
    pos = 'v' if is_verb else 'n'
    return _wnl.lemmatize(t, pos=pos)


# Generic linguistic guardrails (not domain mapping)
PRONOUNS = {
    'i','you','he','she','we','they','who','whom','whose','me','him','her','us','them',
    'my','your','his','our','their','yours','hers','ours','theirs'
}
DETERMINERS = {'a','an','the','this','that','these','those'}
STOP_VERBS = {'be','have','do','want'}  # template/aux verbs to ignore in SVO


def normalize_and_link_concepts(session, usid: int) -> Dict[str, str]:
    """Deprecated: Concept-based normalization removed. Use role/object/verb from UserStory."""
    return {}


def normalize_check_exclude(text: str) -> str:
    """Làm sạch concept text: bỏ đại từ, mạo từ và tiền tố sở hữu.

    - Lowercase, trim, split theo khoảng trắng
    - Loại bỏ mọi token thuộc PRONOUNS hoặc DETERMINERS
    - Trả về chuỗi đã lọc; nếu trống, trả ""
    """
    if not text:
        return ""
    tokens = (text or "").lower().strip().split()
    filtered = [w for w in tokens if w not in PRONOUNS and w not in DETERMINERS]
    if not filtered:
        return ""
    return " ".join(filtered)


def compute_and_persist_similarity(session, usid: int, threshold: float = 0.8):
    """Deprecated: Similarity persistence removed in simplified model."""
    return []


# ---- Concept clustering (WordNet + Wu-Palmer + optional vectors) ----


def _best_synset(word: str, is_verb: bool):
    if wn is None:
        return None
    pos = wn.VERB if is_verb else wn.NOUN
    syns = wn.synsets(word, pos=pos)
    return syns[0] if syns else None


def _vector_similarity(nlp, a: str, b: str) -> float:
    try:
        if nlp is None:
            return 0.0
        ta = nlp(a)
        tb = nlp(b)
        if not ta.vector_norm or not tb.vector_norm:
            return 0.0
        return float(ta.similarity(tb))
    except Exception:
        return 0.0


def _w2v_similarity(a: str, b: str) -> float:
    try:
        model = _load_w2v_model()
        if model is None:
            return 0.0
        if a in model.key_to_index and b in model.key_to_index:
            return float(model.similarity(a, b))
        return 0.0
    except Exception:
        return 0.0


def _semantic_similarity(nlp, a: str, b: str) -> float:
    """Combine spaCy vector similarity and optional word2vec; return the max."""
    return max(_vector_similarity(nlp, a, b), _w2v_similarity(a, b))


def combined_similarity(a: str, b: str) -> float:
    """Average Wu-Palmer and word2vec similarities.

    - Wu-Palmer: max over all synset pairs (noun sense)
    - Word2Vec: cosine similarity if both tokens in vocab
    """
    try:
        # Wu-Palmer
        wup = 0.0
        if wn is not None:
            syns1 = wn.synsets(a)
            syns2 = wn.synsets(b)
            if syns1 and syns2:
                best = 0.0
                for s1 in syns1:
                    for s2 in syns2:
                        sim = s1.wup_similarity(s2) or 0.0
                        if sim and sim > best:
                            best = float(sim)
                wup = float(best)
        # Word2Vec
        w2v = _w2v_similarity(a, b)
        # Average
        return float((wup + w2v) / 2.0)
    except Exception:
        return 0.0


# Optional domain keywords for auto-labeling
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "authentication": ["login", "register", "logout", "password", "account"],
    "profile": ["profile", "update", "edit", "avatar", "settings"],
}


def cluster_concepts(concepts: List[str], pair_similarities: List[Tuple[str, str, float]], threshold: float = 0.7) -> List[List[str]]:
    """Cluster concepts using union-find over pairs with similarity >= threshold."""
    if not concepts:
        return []
    idx = {c: i for i, c in enumerate(concepts)}
    parent = list(range(len(concepts)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b, s in pair_similarities:
        if s is None:
            continue
        if float(s) >= float(threshold):
            if a in idx and b in idx:
                union(idx[a], idx[b])

    groups: Dict[int, List[str]] = {}
    for c in concepts:
        r = find(idx[c])
        groups.setdefault(r, []).append(c)
    return list(groups.values())


def label_cluster(members: List[str]) -> str | None:
    """Auto-label cluster using keyword mapping; fallback to most frequent token.

    Note: A simple heuristic. Can be replaced by WordNet hypernym selection later.
    """
    lows = [m.lower() for m in members]
    # Keyword matching score
    best_label = None
    best_score = 0
    for label, kws in DOMAIN_KEYWORDS.items():
        score = sum(1 for w in lows if w in kws)
        if score > best_score:
            best_score = score
            best_label = label
    if best_label:
        return best_label
    # Fallback: shortest member name as label
    return sorted(members, key=lambda s: (len(s or ''), s or ''))[0] if members else None


def _wn_canonical(term: str, is_verb: bool) -> str | None:
    """Pick a canonical lemma from WordNet for a term based on the most frequent sense.

    Returns a space-separated lemma or None if no synset is found.
    """
    if wn is None or not term:
        return None
    # Avoid pronouns/determiners going to unrelated proper nouns (e.g., WHO -> World Health Organization)
    low = term.strip().lower()
    if not is_verb and (low in PRONOUNS or low in DETERMINERS):
        return low
    q = term.replace(" ", "_")
    syns = wn.synsets(q, pos=wn.VERB if is_verb else wn.NOUN)
    if not syns:
        return None
    s0 = syns[0]
    # choose lemma with max count in first synset
    best = None
    best_count = -1
    for l in s0.lemmas():
        cnt = l.count() if hasattr(l, 'count') else 0
        if cnt > best_count:
            best = l
            best_count = cnt
    name = (best.name() if best is not None else s0.lemmas()[0].name())
    return name.replace('_', ' ')


def cluster_concepts_and_persist(session, usid: int, nlp=None, wup_threshold: float = 0.9, vec_threshold: float = 0.75):
    """Deprecated: clustering on Concept table removed in simplified model."""
    return {}


def _choose_canonical(terms: List[str], concept_type: str, comps: List[Any]) -> str:
    """Deprecated: canonical choice for Concept-based clustering removed."""
    # Fallback: choose shortest
    if not terms:
        return ''
    return sorted(terms, key=lambda s: (len(s or ''), s or ''))[0]


def build_normalized_svo_from_user_story(session, usid: int, nlp=None) -> List[Dict[str, Any]]:
    """Build normalized SVO triples directly from UserStory (role/verb/object)."""
    story: UserStory | None = session.query(UserStory).filter(UserStory.usid == usid).first()
    if not story:
        return []
    role = (story.role or '').strip()
    verb = (story.verb or '').strip()
    obj = (story.object or '').strip()
    if not (role or verb or obj):
        return []
    if verb.lower() in STOP_VERBS:
        verb = ''
    if role and role.lower() in PRONOUNS:
        role = ''
    role_norm = _wn_canonical(role, is_verb=False) or _lemmatize(role, is_verb=False) if role else ''
    verb_norm = _wn_canonical(verb, is_verb=True) or _lemmatize(verb, is_verb=True) if verb else ''
    obj_norm = _wn_canonical(obj, is_verb=False) or _lemmatize(obj, is_verb=False) if obj else ''
    return [{
        'user_story_db_id': usid,
        'subject': role_norm,
        'verb': verb_norm,
        'object': obj_norm,
    }]


def build_pairwise_api(normalized_svo: List[Dict[str, Any]], nlp=None) -> List[Dict[str, Any]]:
    """Create pair-wise relationships across subjects and across objects (API only), including similarity."""
    subjects = sorted({r.get('subject') for r in normalized_svo if r.get('subject')})
    objects = sorted({r.get('object') for r in normalized_svo if r.get('object')})
    api_pairs: List[Dict[str, Any]] = []
    for a, b in combinations(subjects, 2):
        sim = _semantic_similarity(nlp, a, b)
        api_pairs.append({'type': 'subject', 'a': a, 'b': b, 'similarity': sim})
    for a, b in combinations(objects, 2):
        sim = _semantic_similarity(nlp, a, b)
        api_pairs.append({'type': 'object', 'a': a, 'b': b, 'similarity': sim})
    return api_pairs

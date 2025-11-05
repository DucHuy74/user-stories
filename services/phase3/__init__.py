import logging
from typing import Dict, List, Any
from database import DatabaseSession, get_database_manager
from .helpers import (
    generate_synonym_records,
    combined_similarity,
    cluster_concepts,
    label_cluster,
    normalize_check_exclude,
    PRONOUNS,
    DETERMINERS,
)
from .helpers import wn
from models import ProcessingSession
from models.concept import Concept
from models import SvoRelationship


class Phase3:
    def __init__(self, session_id: str = None):
        self.input_data = {}
        self.synonyms = {}
        self.similarities = []
        self.final_output = {}
        self.session_id = session_id
        self.db_manager = get_database_manager()
        # Phase 3 no longer uses spaCy; semantic similarity will rely on word2vec if available

    def process_wordnet(self, phase2_data: Dict = None) -> Dict:
        if phase2_data:
            self.input_data = phase2_data
            self.session_id = phase2_data.get("session_id")

        with DatabaseSession(self.db_manager) as session:
            # 1) Load Phase 2 concepts (objects only) and filter out pronouns/determiners
            concepts = session.query(Concept).all()
            concept_texts: List[str] = []
            for c in concepts:
                t = (c.text_object_as_concept_domain or '').strip()
                if not t:
                    continue
                t = normalize_check_exclude(t)
                if not t:
                    continue
                concept_texts.append(t)
            concept_texts = sorted(set(concept_texts))

            # 2) Synonym expansion via WordNet
            synonym_records = generate_synonym_records([{ 'text': t } for t in concept_texts])

            # 2.5) Normalize each concept to a canonical synonym from WordNet
            def get_canonical_synonym(word: str) -> str:
                try:
                    from nltk.corpus import wordnet as wn_local
                except Exception:
                    return (word or '').lower()
                synsets = wn_local.synsets(word)
                if not synsets:
                    return (word or '').lower()
                try:
                    lemma = synsets[0].lemmas()[0].name().replace('_', ' ')
                    return (lemma or '').lower()
                except Exception:
                    return (word or '').lower()

            normalized_concepts: List[str] = [get_canonical_synonym(t) for t in concept_texts]
            canonical_map = dict(zip(concept_texts, normalized_concepts))
            concept_texts = sorted(set(normalized_concepts))

            # 3) Pairwise similarity (combined Wu-Palmer + Word2Vec average)
            from itertools import combinations
            pairs: List[Dict[str, Any]] = []
            for a, b in combinations(concept_texts, 2):
                similarity = combined_similarity(a, b)
                pairs.append({ 'a': a, 'b': b, 'similarity': similarity, 'type': 'object' })

            # 4) Cluster concepts and label domains
            tuple_pairs = [(p['a'], p['b'], p['similarity']) for p in pairs]
            clusters = cluster_concepts(concept_texts, tuple_pairs, threshold=0.7)
            # Map concept -> label
            concept_label: Dict[str, str | None] = {}
            for grp in clusters:
                lbl = label_cluster(grp)
                for m in grp:
                    concept_label[m] = lbl

            # 5) Persist relationships with method and domain label (store canonical terms)
            for p in pairs:
                a_can = canonical_map.get(p['a'], p['a'])
                b_can = canonical_map.get(p['b'], p['b'])
                lbl = concept_label.get(a_can) or concept_label.get(b_can)
                session.add(SvoRelationship(a=a_can, b=b_can, similarity=p['similarity'], type=p['type'], method='combined', domain_label=lbl))

            # 6) Final output for API
            self.final_output = {
                'concepts': concept_texts,
                'synonyms': synonym_records,
                'pairwise_relationships': pairs,
                'clusters': [
                    { 'label': label_cluster(g), 'members': sorted(g) }
                    for g in clusters
                ],
                'session_id': self.session_id,
            }
            self._update_processing_session(session, 3, 'completed')

        logging.info("✅ Phase 3 completed")
    

        return self.final_output

    def _create_final_output(self, normalized_svo: List[Dict[str, Any]], pairwise: List[Dict[str, Any]]):
        # Legacy no-op kept for backward compatibility (no longer used in new flow)
        self.final_output = {
            'user_roles': [],
            'objects': [],
            'verbs': [],
            'normalized_svo': normalized_svo,
            'subject_verb_object': normalized_svo,
            'pairwise_relationships': pairwise,
            'synonyms': {},
            'session_id': self.session_id,
        }

    def _update_processing_session(self, session, phase_completed: int, status: str):
        processing_session = session.query(ProcessingSession).filter_by(id=self.session_id).first()
        if processing_session:
            processing_session.phase_completed = phase_completed
            processing_session.status = status
            if status == "completed":
                from datetime import datetime
                processing_session.completed_at = datetime.utcnow()

    def get_results(self):
        return self.final_output

"""
Query enhancement engine for improving query understanding and expansion.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict, Counter
import unicodedata

from src.models.base import EnhancedQuery, QueryIntent, AmbiguityReport, ConversationContext
from config.settings import config


logger = logging.getLogger(__name__)


@dataclass
class SynonymEntry:
    """Entry in synonym dictionary."""
    term: str
    synonyms: List[str]
    domain: str
    weight: float = 1.0


@dataclass
class SpellCorrectionResult:
    """Result of spell correction."""
    original_term: str
    corrected_term: str
    confidence: float
    suggestions: List[str]


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    detected_language: str
    confidence: float
    supported_languages: List[str]


@dataclass
class ClarificationQuestion:
    """Clarification question with context."""
    question: str
    question_type: str  # ambiguous_term, vague_query, multiple_intent, language
    context: Dict[str, Any]
    priority: int  # 1 = high, 2 = medium, 3 = low


class QueryEnhancerInterface:
    """Interface for query enhancement."""
    
    def enhance_query(self, query: str, context: Optional[ConversationContext] = None) -> EnhancedQuery:
        """Enhance query with expansion, correction, and intent detection."""
        raise NotImplementedError
    
    def expand_terms(self, query: str) -> List[str]:
        """Expand query terms with synonyms and related terms."""
        raise NotImplementedError
    
    def correct_spelling(self, query: str) -> str:
        """Correct spelling errors in query."""
        raise NotImplementedError
    
    def detect_ambiguity(self, query: str) -> AmbiguityReport:
        """Detect query ambiguity and suggest clarifications."""
        raise NotImplementedError
    
    def detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent."""
        raise NotImplementedError
    
    def detect_language(self, query: str) -> LanguageDetectionResult:
        """Detect query language."""
        raise NotImplementedError
    
    def generate_clarification_questions(self, query: str, ambiguity_report: AmbiguityReport) -> List[ClarificationQuestion]:
        """Generate prioritized clarification questions."""
        raise NotImplementedError


class QueryEnhancer(QueryEnhancerInterface):
    """Implementation of query enhancement engine."""
    
    def __init__(self, vocabulary_path: Optional[str] = None):
        """Initialize query enhancer."""
        self.vocabulary_path = vocabulary_path or "data/vocabulary"
        self.synonyms: Dict[str, SynonymEntry] = {}
        self.technical_terms: Set[str] = set()
        self.common_misspellings: Dict[str, str] = {}
        self.intent_patterns: Dict[QueryIntent, List[str]] = {}
        self.ambiguous_terms: Dict[str, List[str]] = {}
        self.language_patterns: Dict[str, List[str]] = {}
        self.clarification_templates: Dict[str, str] = {}
        
        # Initialize components
        self._load_domain_vocabulary()
        self._load_synonym_dictionary()
        self._load_spell_correction_data()
        self._initialize_intent_patterns()
        self._load_ambiguity_patterns()
        self._initialize_language_patterns()
        self._initialize_clarification_templates()
    
    def enhance_query(self, query: str, context: Optional[ConversationContext] = None) -> EnhancedQuery:
        """Enhance query with expansion, correction, and intent detection."""
        try:
            logger.info(f"Enhancing query: {query}")
            
            # Step 1: Correct spelling
            corrected_query = self.correct_spelling(query)
            
            # Step 2: Expand terms
            expanded_terms = self.expand_terms(corrected_query)
            
            # Step 3: Detect intent
            intent = self.detect_intent(corrected_query)
            
            # Step 4: Extract filters from query
            filters = self._extract_filters(corrected_query)
            
            # Step 5: Determine context dependency
            context_dependent = self._is_context_dependent(corrected_query, context)
            
            enhanced_query = EnhancedQuery(
                original_query=query,
                expanded_terms=expanded_terms,
                corrected_query=corrected_query,
                intent=intent,
                filters=filters,
                context_dependent=context_dependent
            )
            
            logger.info(f"Query enhanced successfully. Intent: {intent}, Expanded terms: {len(expanded_terms)}")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"Error enhancing query: {e}")
            # Return basic enhanced query on error
            return EnhancedQuery(
                original_query=query,
                expanded_terms=[query],
                corrected_query=query,
                intent=QueryIntent.FACTUAL,
                filters={},
                context_dependent=False
            )
    
    def expand_terms(self, query: str) -> List[str]:
        """Expand query terms with synonyms and related terms."""
        try:
            expanded_terms = [query]  # Always include original query
            
            # Tokenize query
            tokens = self._tokenize_query(query)
            
            # Find synonyms for each token
            for token in tokens:
                token_lower = token.lower()
                
                # Check direct synonyms
                if token_lower in self.synonyms:
                    synonym_entry = self.synonyms[token_lower]
                    expanded_terms.extend(synonym_entry.synonyms)
                
                # Check partial matches for compound terms
                partial_synonyms = self._find_partial_synonyms(token_lower)
                expanded_terms.extend(partial_synonyms)
            
            # Generate phrase variations
            phrase_variations = self._generate_phrase_variations(query, tokens)
            expanded_terms.extend(phrase_variations)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_expanded = []
            for term in expanded_terms:
                if term.lower() not in seen:
                    seen.add(term.lower())
                    unique_expanded.append(term)
            
            logger.debug(f"Expanded '{query}' to {len(unique_expanded)} terms")
            return unique_expanded
            
        except Exception as e:
            logger.error(f"Error expanding terms: {e}")
            return [query]
    
    def correct_spelling(self, query: str) -> str:
        """Correct spelling errors in query."""
        try:
            tokens = self._tokenize_query(query)
            corrected_tokens = []
            
            for token in tokens:
                # Skip very short tokens and numbers
                if len(token) <= 2 or token.isdigit():
                    corrected_tokens.append(token)
                    continue
                
                token_lower = token.lower()
                
                # Check if token is a known technical term
                if token_lower in self.technical_terms:
                    corrected_tokens.append(token)
                    continue
                
                # Check common misspellings
                if token_lower in self.common_misspellings:
                    corrected_tokens.append(self.common_misspellings[token_lower])
                    continue
                
                # Find best match using fuzzy matching
                best_match = self._find_best_spelling_match(token_lower)
                if best_match and best_match != token_lower:
                    corrected_tokens.append(best_match)
                    logger.debug(f"Corrected '{token}' to '{best_match}'")
                else:
                    corrected_tokens.append(token)
            
            corrected_query = " ".join(corrected_tokens)
            return corrected_query
            
        except Exception as e:
            logger.error(f"Error correcting spelling: {e}")
            return query
    
    def detect_ambiguity(self, query: str) -> AmbiguityReport:
        """Detect query ambiguity and suggest clarifications."""
        try:
            tokens = self._tokenize_query(query)
            
            # Use enhanced ambiguity scoring
            ambiguity_score, clarification_questions, suggested_interpretations = self._enhanced_ambiguity_scoring(query, tokens)
            
            # Check for multiple possible intents
            possible_intents = self._detect_multiple_intents(query)
            if len(possible_intents) > 1:
                ambiguity_score += 0.15
                intent_names = [intent.value for intent in possible_intents]
                clarification_questions.append(f"Are you looking for: {', '.join(intent_names)}?")
            
            # Language detection for additional context
            language_result = self.detect_language(query)
            if language_result.detected_language != 'english' and language_result.confidence > 0.8:
                ambiguity_score += 0.1  # Slight increase for non-English queries
                clarification_questions.append(f"I detected this might be in {language_result.detected_language}. Should I respond in English?")
            
            is_ambiguous = ambiguity_score > 0.3
            
            return AmbiguityReport(
                is_ambiguous=is_ambiguous,
                ambiguity_score=min(ambiguity_score, 1.0),
                clarification_questions=clarification_questions[:3],  # Limit to 3 questions
                suggested_interpretations=suggested_interpretations[:5]  # Limit to 5 interpretations
            )
            
        except Exception as e:
            logger.error(f"Error detecting ambiguity: {e}")
            return AmbiguityReport(
                is_ambiguous=False,
                ambiguity_score=0.0,
                clarification_questions=[],
                suggested_interpretations=[]
            )
    
    def detect_intent(self, query: str) -> QueryIntent:
        """Detect query intent."""
        try:
            query_lower = query.lower()
            intent_scores = defaultdict(float)
            
            # Check patterns for each intent
            for intent, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        intent_scores[intent] += 1.0
            
            # Additional heuristics
            # Factual questions
            if any(word in query_lower for word in ['what is', 'define', 'definition', 'meaning']):
                intent_scores[QueryIntent.FACTUAL] += 0.8
            
            # Procedural questions
            if any(word in query_lower for word in ['how to', 'steps', 'procedure', 'process']):
                intent_scores[QueryIntent.PROCEDURAL] += 0.8
            
            # Comparative questions
            if any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs', 'better']):
                intent_scores[QueryIntent.COMPARATIVE] += 0.8
            
            # Troubleshooting questions
            if any(word in query_lower for word in ['error', 'problem', 'issue', 'fix', 'solve']):
                intent_scores[QueryIntent.TROUBLESHOOTING] += 0.8
            
            # Return intent with highest score, default to FACTUAL
            if intent_scores:
                best_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
                return best_intent
            
            return QueryIntent.FACTUAL
            
        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return QueryIntent.FACTUAL
    
    def _load_domain_vocabulary(self):
        """Load domain-specific vocabulary."""
        try:
            # Create vocabulary directory if it doesn't exist
            vocab_dir = Path(self.vocabulary_path)
            vocab_dir.mkdir(parents=True, exist_ok=True)
            
            # Load technical terms from file or create default
            terms_file = vocab_dir / "technical_terms.txt"
            if terms_file.exists():
                with open(terms_file, 'r', encoding='utf-8') as f:
                    self.technical_terms = set(line.strip().lower() for line in f if line.strip())
            else:
                # Create default technical terms (French and English)
                default_terms = [
                    # French ICT terms
                    "algorithme", "bande passante", "fréquence", "modulation", "antenne",
                    "signal", "bruit", "canal", "protocole", "réseau", "sans fil",
                    "communication", "transmission", "récepteur", "émetteur",
                    "codage", "décodage", "chiffrement", "déchiffrement", "sécurité",
                    "authentification", "autorisation", "pare-feu", "routeur", "commutateur",
                    "informatique", "télécommunications", "numérique", "analogique",
                    "internet", "wifi", "bluetooth", "ethernet", "tcp", "udp", "ip",
                    "serveur", "client", "base de données", "programmation", "logiciel",
                    "matériel", "système", "architecture", "interface", "application",
                    # English equivalents for mixed usage
                    "algorithm", "bandwidth", "frequency", "modulation", "antenna",
                    "signal", "noise", "channel", "protocol", "network", "wireless",
                    "communication", "transmission", "receiver", "transmitter",
                    "coding", "decoding", "encryption", "decryption", "security",
                    "authentication", "authorization", "firewall", "router", "switch"
                ]
                self.technical_terms = set(default_terms)
                
                # Save default terms
                with open(terms_file, 'w', encoding='utf-8') as f:
                    for term in sorted(default_terms):
                        f.write(f"{term}\n")
            
            logger.info(f"Loaded {len(self.technical_terms)} technical terms")
            
        except Exception as e:
            logger.error(f"Error loading domain vocabulary: {e}")
            self.technical_terms = set()
    
    def _load_synonym_dictionary(self):
        """Load synonym dictionary."""
        try:
            vocab_dir = Path(self.vocabulary_path)
            synonyms_file = vocab_dir / "synonyms.json"
            
            if synonyms_file.exists():
                with open(synonyms_file, 'r', encoding='utf-8') as f:
                    synonyms_data = json.load(f)
                    
                for term, data in synonyms_data.items():
                    self.synonyms[term.lower()] = SynonymEntry(
                        term=term,
                        synonyms=data.get('synonyms', []),
                        domain=data.get('domain', 'general'),
                        weight=data.get('weight', 1.0)
                    )
            else:
                # Create default synonyms (French-focused)
                default_synonyms = {
                    # French terms
                    "réseau": {
                        "synonyms": ["network", "système", "infrastructure", "topologie", "net"],
                        "domain": "networking",
                        "weight": 1.0
                    },
                    "sans fil": {
                        "synonyms": ["wireless", "radio", "rf", "cellulaire", "mobile", "wifi"],
                        "domain": "communications",
                        "weight": 1.0
                    },
                    "signal": {
                        "synonyms": ["onde", "transmission", "porteuse", "waveform"],
                        "domain": "communications",
                        "weight": 1.0
                    },
                    "algorithme": {
                        "synonyms": ["algorithm", "méthode", "procédure", "technique", "approche"],
                        "domain": "computer_science",
                        "weight": 1.0
                    },
                    "protocole": {
                        "synonyms": ["protocol", "standard", "spécification", "format"],
                        "domain": "networking",
                        "weight": 1.0
                    },
                    "sécurité": {
                        "synonyms": ["security", "protection", "chiffrement", "encryption"],
                        "domain": "security",
                        "weight": 1.0
                    },
                    "communication": {
                        "synonyms": ["télécommunication", "échange", "transmission", "liaison"],
                        "domain": "communications",
                        "weight": 1.0
                    },
                    "informatique": {
                        "synonyms": ["computer science", "IT", "technologie", "numérique"],
                        "domain": "computer_science",
                        "weight": 1.0
                    },
                    # English terms for mixed usage
                    "network": {
                        "synonyms": ["réseau", "net", "system", "infrastructure", "topology"],
                        "domain": "networking",
                        "weight": 1.0
                    },
                    "wireless": {
                        "synonyms": ["sans fil", "radio", "rf", "cellular", "mobile"],
                        "domain": "communications",
                        "weight": 1.0
                    },
                    "algorithm": {
                        "synonyms": ["algorithme", "method", "procedure", "technique", "approach"],
                        "domain": "computer_science",
                        "weight": 1.0
                    }
                }
                
                # Save default synonyms
                with open(synonyms_file, 'w', encoding='utf-8') as f:
                    json.dump(default_synonyms, f, indent=2, ensure_ascii=False)
                
                # Load default synonyms
                for term, data in default_synonyms.items():
                    self.synonyms[term.lower()] = SynonymEntry(
                        term=term,
                        synonyms=data['synonyms'],
                        domain=data['domain'],
                        weight=data['weight']
                    )
            
            logger.info(f"Loaded {len(self.synonyms)} synonym entries")
            
        except Exception as e:
            logger.error(f"Error loading synonym dictionary: {e}")
            self.synonyms = {}
    
    def _load_spell_correction_data(self):
        """Load spell correction data."""
        try:
            vocab_dir = Path(self.vocabulary_path)
            misspellings_file = vocab_dir / "common_misspellings.json"
            
            if misspellings_file.exists():
                with open(misspellings_file, 'r', encoding='utf-8') as f:
                    self.common_misspellings = json.load(f)
            else:
                # Create default misspellings (French and English)
                default_misspellings = {
                    # French misspellings
                    "algorythme": "algorithme",
                    "algortime": "algorithme",
                    "reseaux": "réseau",
                    "reseau": "réseau",
                    "protocoll": "protocole",
                    "protocal": "protocole",
                    "comunication": "communication",
                    "comunicaton": "communication",
                    "securite": "sécurité",
                    "securité": "sécurité",
                    "chifrement": "chiffrement",
                    "chiffremnt": "chiffrement",
                    "authentifcation": "authentification",
                    "authentification": "authentification",
                    "informatque": "informatique",
                    "informatic": "informatique",
                    "telecommunication": "télécommunication",
                    "telecomunication": "télécommunication",
                    # English misspellings
                    "algoritm": "algorithm",
                    "recieve": "receive",
                    "transmision": "transmission",
                    "bandwith": "bandwidth",
                    "frequancy": "frequency",
                    "modualtion": "modulation",
                    "encription": "encryption"
                }
                
                self.common_misspellings = default_misspellings
                
                # Save default misspellings
                with open(misspellings_file, 'w', encoding='utf-8') as f:
                    json.dump(default_misspellings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Loaded {len(self.common_misspellings)} common misspellings")
            
        except Exception as e:
            logger.error(f"Error loading spell correction data: {e}")
            self.common_misspellings = {}
    
    def _initialize_intent_patterns(self):
        """Initialize intent detection patterns."""
        self.intent_patterns = {
            QueryIntent.FACTUAL: [
                # French patterns
                r'\b(qu\'est-ce que|définir|définition|signification|expliquer|c\'est quoi)\b',
                r'\b(qu\'est-ce|que signifie|quelle est)\b',
                r'\b(parlez-moi de|dites-moi)\b',
                # English patterns
                r'\b(what|define|definition|meaning|explain)\b',
                r'\bis\b.*\?',
                r'\bwhat\s+is\b',
                r'\btell\s+me\s+about\b'
            ],
            QueryIntent.PROCEDURAL: [
                # French patterns
                r'\b(comment|étapes|procédure|processus|méthode)\b',
                r'\bcomment\s+(faire|configurer|installer|utiliser)\b',
                r'\b(étapes pour|procédure pour|marche à suivre)\b',
                # English patterns
                r'\b(how|steps|procedure|process|method)\b',
                r'\bhow\s+to\b',
                r'\bsteps\s+to\b',
                r'\bprocedure\s+for\b'
            ],
            QueryIntent.CONCEPTUAL: [
                # French patterns
                r'\b(concept|théorie|principe|idée|notion)\b',
                r'\bpourquoi\s+(est-ce que|fait)\b',
                r'\bexpliquer\s+le\s+concept\b',
                # English patterns
                r'\b(concept|theory|principle|idea)\b',
                r'\bwhy\s+does\b',
                r'\bwhy\s+is\b',
                r'\bexplain\s+the\s+concept\b'
            ],
            QueryIntent.COMPARATIVE: [
                # French patterns
                r'\b(comparer|comparaison|différence|versus|vs|mieux|meilleur)\b',
                r'\bdifférence\s+entre\b',
                r'\bcomparer\s+.*\s+(avec|et)\b',
                r'\b(lequel|laquelle)\s+est\s+(mieux|meilleur)\b',
                # English patterns
                r'\b(compare|comparison|difference|versus|vs|better)\b',
                r'\bdifference\s+between\b',
                r'\bcompare\s+.*\s+with\b',
                r'\bwhich\s+is\s+better\b'
            ],
            QueryIntent.TROUBLESHOOTING: [
                # French patterns
                r'\b(erreur|problème|issue|réparer|résoudre|déboguer|dépanner)\b',
                r'\b(ne fonctionne pas|ne marche pas|en panne)\b',
                r'\b(échec|failed|comment réparer|comment résoudre)\b',
                # English patterns
                r'\b(error|problem|issue|fix|solve|debug|troubleshoot)\b',
                r'\bnot\s+working\b',
                r'\bfailed\s+to\b',
                r'\bhow\s+to\s+fix\b'
            ]
        }
    
    def _load_ambiguity_patterns(self):
        """Load ambiguity patterns."""
        try:
            vocab_dir = Path(self.vocabulary_path)
            ambiguity_file = vocab_dir / "ambiguous_terms.json"
            
            if ambiguity_file.exists():
                with open(ambiguity_file, 'r', encoding='utf-8') as f:
                    self.ambiguous_terms = json.load(f)
            else:
                # Create default ambiguous terms (French-focused)
                default_ambiguous = {
                    # French ambiguous terms
                    "canal": ["canal de communication", "canal TV", "canal de données"],
                    "trame": ["trame de données", "trame temporelle", "trame de référence"],
                    "signal": ["signal électrique", "signal numérique", "signal analogique"],
                    "réseau": ["réseau informatique", "réseau de télécommunication", "réseau social"],
                    "protocole": ["protocole réseau", "protocole de communication", "protocole de sécurité"],
                    "interface": ["interface utilisateur", "interface réseau", "interface logicielle"],
                    "système": ["système informatique", "système d'exploitation", "système de communication"],
                    # English equivalents
                    "channel": ["communication channel", "TV channel", "data channel"],
                    "frame": ["data frame", "time frame", "reference frame"],
                    "network": ["computer network", "communication network", "social network"],
                    "protocol": ["network protocol", "communication protocol", "security protocol"]
                }
                
                self.ambiguous_terms = default_ambiguous
                
                # Save default ambiguous terms
                with open(ambiguity_file, 'w', encoding='utf-8') as f:
                    json.dump(default_ambiguous, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Loaded {len(self.ambiguous_terms)} ambiguous terms")
            
        except Exception as e:
            logger.error(f"Error loading ambiguity patterns: {e}")
            self.ambiguous_terms = {}
    
    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize query into words."""
        # Simple tokenization - split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', query.lower())
        return tokens
    
    def _find_partial_synonyms(self, token: str) -> List[str]:
        """Find synonyms for partial matches."""
        partial_synonyms = []
        
        for term, synonym_entry in self.synonyms.items():
            if token in term or term in token:
                partial_synonyms.extend(synonym_entry.synonyms)
        
        return partial_synonyms
    
    def _generate_phrase_variations(self, query: str, tokens: List[str]) -> List[str]:
        """Generate phrase variations."""
        variations = []
        
        # Generate variations by replacing individual words with synonyms
        for i, token in enumerate(tokens):
            if token in self.synonyms:
                for synonym in self.synonyms[token].synonyms:
                    new_tokens = tokens.copy()
                    new_tokens[i] = synonym
                    variations.append(" ".join(new_tokens))
        
        return variations
    
    def _find_best_spelling_match(self, token: str) -> Optional[str]:
        """Find best spelling match using fuzzy matching."""
        if len(token) < 3:
            return None
        
        best_match = None
        best_ratio = 0.0
        threshold = 0.8
        
        # Check against technical terms
        for term in self.technical_terms:
            ratio = SequenceMatcher(None, token, term).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = term
        
        # Check against synonym keys
        for term in self.synonyms.keys():
            ratio = SequenceMatcher(None, token, term).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = term
        
        return best_match
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters from query."""
        filters = {}
        query_lower = query.lower()
        
        # Extract document type filters (French and English)
        doc_type_mapping = {
            # French terms
            'pdf': 'pdf',
            'diapositive': 'slide',
            'diapositives': 'slide', 
            'présentation': 'slide',
            'exercice': 'exercise',
            'exercices': 'exercise',
            'td': 'exercise',  # Travaux Dirigés
            'tp': 'exercise',  # Travaux Pratiques
            'syllabus': 'syllabus',
            'programme': 'syllabus',
            'cours': 'course',
            'leçon': 'lesson',
            'chapitre': 'chapter',
            # English terms
            'slide': 'slide',
            'slides': 'slide',
            'exercise': 'exercise',
            'exercises': 'exercise',
            'lesson': 'lesson',
            'chapter': 'chapter'
        }
        
        for term, doc_type in doc_type_mapping.items():
            if term in query_lower:
                filters['document_type'] = doc_type
                break
        
        # Extract course module filters (French and English)
        module_mapping = {
            # French terms
            'partie 1': 'part1',
            'partie 2': 'part2', 
            'partie 3': 'part3',
            'partie 4': 'part4',
            'partie1': 'part1',
            'partie2': 'part2',
            'partie3': 'part3', 
            'partie4': 'part4',
            'chapitre 1': 'chapter1',
            'chapitre 2': 'chapter2',
            'chapitre 3': 'chapter3',
            'série': 'serie',
            'serie': 'serie',
            'td1': 'td1',
            'td2': 'td2',
            'td3': 'td3',
            'tp1': 'tp1',
            'tp2': 'tp2',
            'tp3': 'tp3',
            # English terms
            'part1': 'part1',
            'part2': 'part2',
            'part3': 'part3', 
            'part4': 'part4',
            'chapter': 'chapter',
            'serie': 'serie'
        }
        
        for term, module in module_mapping.items():
            if term in query_lower:
                filters['course_module'] = module
                break
        
        return filters
    
    def _is_context_dependent(self, query: str, context: Optional[ConversationContext]) -> bool:
        """Determine if query is context dependent."""
        if not context:
            return False
        
        # Check for pronouns and references
        context_indicators = [
            r'\b(this|that|it|they|them|these|those)\b',
            r'\b(above|below|previous|earlier|before)\b',
            r'\b(also|too|as well|additionally)\b'
        ]
        
        for pattern in context_indicators:
            if re.search(pattern, query.lower()):
                return True
        
        return False
    
    def _detect_multiple_intents(self, query: str) -> List[QueryIntent]:
        """Detect multiple possible intents."""
        possible_intents = []
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    if intent not in possible_intents:
                        possible_intents.append(intent)
                    break
        
        return possible_intents
    
    def detect_language(self, query: str) -> LanguageDetectionResult:
        """Detect query language."""
        try:
            query_lower = query.lower()
            language_scores = defaultdict(float)
            
            # Check for language-specific patterns
            for language, patterns in self.language_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, query_lower):
                        language_scores[language] += 1.0
            
            # Check for character-based detection
            # French indicators
            french_chars = ['à', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'ü', 'ÿ', 'ç']
            if any(char in query for char in french_chars):
                language_scores['french'] += 2.0
            
            # Arabic indicators
            arabic_range = range(0x0600, 0x06FF)
            if any(ord(char) in arabic_range for char in query):
                language_scores['arabic'] += 3.0
            
            # Default to English if no strong indicators
            if not language_scores:
                language_scores['english'] = 1.0
            
            # Determine best language
            best_language = max(language_scores.items(), key=lambda x: x[1])
            confidence = min(best_language[1] / 3.0, 1.0)  # Normalize confidence
            
            return LanguageDetectionResult(
                detected_language=best_language[0],
                confidence=confidence,
                supported_languages=['english', 'french', 'arabic']
            )
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return LanguageDetectionResult(
                detected_language='english',
                confidence=0.5,
                supported_languages=['english', 'french', 'arabic']
            )
    
    def generate_clarification_questions(self, query: str, ambiguity_report: AmbiguityReport) -> List[ClarificationQuestion]:
        """Generate prioritized clarification questions."""
        try:
            clarification_questions = []
            
            # Generate questions based on ambiguity report
            if ambiguity_report.is_ambiguous or ambiguity_report.ambiguity_score > 0.2:
                
                # High priority: Ambiguous terms
                for i, interpretation in enumerate(ambiguity_report.suggested_interpretations[:3]):
                    question = ClarificationQuestion(
                        question=f"Are you asking about '{interpretation}'?",
                        question_type="ambiguous_term",
                        context={"interpretation": interpretation, "original_query": query},
                        priority=1
                    )
                    clarification_questions.append(question)
                
                # Medium priority: Multiple intents
                possible_intents = self._detect_multiple_intents(query)
                if len(possible_intents) > 1:
                    intent_names = [intent.value for intent in possible_intents[:2]]
                    question = ClarificationQuestion(
                        question=f"Are you looking for {' or '.join(intent_names)} information?",
                        question_type="multiple_intent",
                        context={"intents": intent_names, "original_query": query},
                        priority=2
                    )
                    clarification_questions.append(question)
                
                # Low priority: General clarification
                if ambiguity_report.ambiguity_score > 0.5:
                    question = ClarificationQuestion(
                        question="Could you provide more specific details about what you're looking for?",
                        question_type="vague_query",
                        context={"ambiguity_score": ambiguity_report.ambiguity_score, "original_query": query},
                        priority=3
                    )
                    clarification_questions.append(question)
            
            # Language-specific clarifications
            language_result = self.detect_language(query)
            if language_result.detected_language != 'english' and language_result.confidence > 0.7:
                question = ClarificationQuestion(
                    question=f"I detected your query might be in {language_result.detected_language}. Would you like to continue in English or {language_result.detected_language}?",
                    question_type="language",
                    context={"detected_language": language_result.detected_language, "confidence": language_result.confidence},
                    priority=1
                )
                clarification_questions.append(question)
            
            # Sort by priority and limit to top 3
            clarification_questions.sort(key=lambda x: x.priority)
            return clarification_questions[:3]
            
        except Exception as e:
            logger.error(f"Error generating clarification questions: {e}")
            return []
    
    def _initialize_language_patterns(self):
        """Initialize language detection patterns."""
        self.language_patterns = {
            'french': [
                # Question words
                r'\b(qu\'est-ce que|comment|pourquoi|où|quand|qui|que|quoi)\b',
                # Articles and determiners
                r'\b(le|la|les|un|une|des|du|de la|ce|cette|ces)\b',
                # Common verbs
                r'\b(est|sont|avoir|être|faire|aller|venir|voir|savoir|pouvoir)\b',
                # Prepositions
                r'\b(avec|sans|pour|dans|sur|sous|entre|parmi|selon)\b',
                # ICT-specific French terms
                r'\b(réseau|protocole|algorithme|sécurité|informatique|télécommunication)\b',
                # Common French phrases
                r'\b(c\'est|il y a|est-ce que|n\'est pas|ne pas)\b'
            ],
            'arabic': [
                r'\b(ما|كيف|لماذا|أين|متى|من)\b',
                r'\b(هو|هي|هم|هن|أنا|أنت)\b',
                r'\b(في|على|تحت|مع|بدون|من)\b'
            ],
            'english': [
                r'\b(what|how|why|where|when|who)\b',
                r'\b(the|a|an|this|that|these|those)\b',
                r'\b(is|are|was|were|have|has|do|does)\b'
            ]
        }
    
    def _initialize_clarification_templates(self):
        """Initialize clarification question templates."""
        self.clarification_templates = {
            'ambiguous_term': {
                'french': "Voulez-vous dire '{term}' dans le sens de : {interpretations} ?",
                'english': "Did you mean '{term}' as in: {interpretations}?"
            },
            'vague_query': {
                'french': "Pourriez-vous être plus spécifique concernant {aspect} ?",
                'english': "Could you be more specific about {aspect}?"
            },
            'multiple_intent': {
                'french': "Cherchez-vous des informations de type {intent_type} ?",
                'english': "Are you looking for {intent_type} information?"
            },
            'language': {
                'french': "J'ai détecté que votre question pourrait être en {language}. Dois-je répondre en {language} ou en français ?",
                'english': "I detected your query might be in {language}. Should I respond in {language} or French?"
            },
            'context_needed': {
                'french': "Cela semble faire référence à quelque chose mentionné précédemment. Pourriez-vous fournir plus de contexte ?",
                'english': "This seems to refer to something mentioned earlier. Could you provide more context?"
            },
            'domain_clarification': {
                'french': "Demandez-vous spécifiquement à propos de {domain} ?",
                'english': "Are you asking about {domain} specifically?"
            }
        }
    
    def _enhanced_ambiguity_scoring(self, query: str, tokens: List[str]) -> Tuple[float, List[str], List[str]]:
        """Enhanced ambiguity scoring with detailed analysis."""
        ambiguity_score = 0.0
        clarification_questions = []
        suggested_interpretations = []
        
        # Check for ambiguous terms with weighted scoring
        ambiguous_term_count = 0
        for token in tokens:
            token_lower = token.lower()
            if token_lower in self.ambiguous_terms:
                ambiguous_term_count += 1
                interpretations = self.ambiguous_terms[token_lower]
                suggested_interpretations.extend(interpretations)
                
                # Weight based on number of interpretations
                weight = min(len(interpretations) * 0.1, 0.3)
                ambiguity_score += weight
                
                clarification = f"Did you mean '{token}' as in: {', '.join(interpretations[:3])}?"
                clarification_questions.append(clarification)
        
        # Penalize multiple ambiguous terms
        if ambiguous_term_count > 1:
            ambiguity_score += 0.2
        
        # Check for vague patterns with context analysis (French and English)
        vague_patterns = [
            # French patterns
            (r'\b(ceci|cela|ça|il|elle|ils|elles)\b', "Pourriez-vous préciser à quoi 'ceci' fait référence ?"),
            (r'\b(comment|quoi|pourquoi)\s*\??\s*$', "Pourriez-vous donner plus de détails sur votre question ?"),
            (r'\b(expliquer|décrire|parlez-moi de)\s*$', "Quel aspect spécifique aimeriez-vous que j'explique ?"),
            (r'\b(aide|aider|support|assistance)\b', "De quelle aide spécifique avez-vous besoin ?"),
            # English patterns
            (r'\b(this|that|it|they)\b', "Could you specify what 'this' refers to?"),
            (r'\b(how|what|why)\s*$', "Could you provide more details about your question?"),
            (r'\b(explain|describe|tell me about)\s*$', "What specific aspect would you like me to explain?"),
            (r'\b(help|assist|support)\b', "What specific help do you need?")
        ]
        
        for pattern, question in vague_patterns:
            if re.search(pattern, query.lower()):
                ambiguity_score += 0.15
                clarification_questions.append(question)
        
        # Check query completeness
        if len(tokens) <= 2:
            ambiguity_score += 0.2
            clarification_questions.append("Could you provide more details about your question?")
        
        # Check for incomplete questions (French and English)
        incomplete_patterns = [
            # French patterns
            r'\b(et alors|et puis|et)\s*\??\s*$',
            r'\b(aussi|également|de même)\s*\??\s*$',
            r'^\s*(et|mais|ou|donc|alors)\b',
            # English patterns
            r'\b(what about|how about|and)\s*$',
            r'\b(also|too|as well)\s*$',
            r'^\s*(and|but|or|so)\b'
        ]
        
        for pattern in incomplete_patterns:
            if re.search(pattern, query.lower()):
                ambiguity_score += 0.25
                clarification_questions.append("This seems to be a follow-up question. Could you provide more context?")
        
        return ambiguity_score, clarification_questions, suggested_interpretations
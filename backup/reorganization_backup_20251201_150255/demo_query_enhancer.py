#!/usr/bin/env python3
"""
Demonstration script for the Query Enhancement Engine.

This script shows how the QueryEnhancer works with various types of queries
including spell correction, term expansion, ambiguity detection, and language detection.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from managers.query_enhancer import QueryEnhancer
from models.base import ConversationContext, Message
from datetime import datetime


def print_separator(title: str):
    """Print a formatted separator."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def demonstrate_query_enhancement():
    """Demonstrate query enhancement capabilities."""
    
    print_separator("Query Enhancement Engine Demo")
    
    # Initialize the query enhancer
    enhancer = QueryEnhancer()
    
    # Test queries with different characteristics (French-focused)
    test_queries = [
        # French spelling errors
        "Qu'est-ce qu'un algorythme de chifrement?",
        
        # French ambiguous terms
        "Qu'est-ce qu'un canal?",
        
        # French vague queries
        "Comment?",
        
        # French clear technical queries
        "Qu'est-ce que la spécification du protocole TCP?",
        
        # French procedural queries
        "Comment configurer les paramètres de sécurité WiFi?",
        
        # French comparative queries
        "Comparer les protocoles TCP et UDP",
        
        # French troubleshooting queries
        "Erreur de connexion réseau réparer",
        
        # Mixed French-English
        "Comment fonctionne le network protocol?",
        
        # English queries (for comparison)
        "What is an algorithm for encryption?",
        "How to configure router settings?",
        
        # Arabic query
        "ما هو بروتوكول الشبكة؟",
        
        # French context-dependent query
        "Parlez-moi plus de ce protocole"
    ]
    
    # Create sample conversation context
    sample_context = ConversationContext(
        conversation_id="demo_conv",
        recent_messages=[
            Message(
                message_id="msg1",
                role="user", 
                content="What is wireless communication?",
                timestamp=datetime.now(),
                sources=[],
                confidence=1.0
            )
        ],
        summary="Discussion about wireless communication",
        relevant_topics=["wireless", "communication"],
        context_tokens=50
    )
    
    for i, query in enumerate(test_queries, 1):
        print_separator(f"Test Query {i}")
        print(f"Original Query: '{query}'")
        
        # Enhance the query
        context = sample_context if "that protocol" in query else None
        enhanced = enhancer.enhance_query(query, context)
        
        print(f"\nEnhanced Query Results:")
        print(f"  Corrected Query: '{enhanced.corrected_query}'")
        print(f"  Detected Intent: {enhanced.intent.value}")
        print(f"  Context Dependent: {enhanced.context_dependent}")
        print(f"  Filters: {enhanced.filters}")
        print(f"  Expanded Terms ({len(enhanced.expanded_terms)}):")
        for j, term in enumerate(enhanced.expanded_terms[:5], 1):
            print(f"    {j}. {term}")
        if len(enhanced.expanded_terms) > 5:
            print(f"    ... and {len(enhanced.expanded_terms) - 5} more")
        
        # Test ambiguity detection
        ambiguity = enhancer.detect_ambiguity(query)
        print(f"\nAmbiguity Analysis:")
        print(f"  Is Ambiguous: {ambiguity.is_ambiguous}")
        print(f"  Ambiguity Score: {ambiguity.ambiguity_score:.2f}")
        
        if ambiguity.clarification_questions:
            print(f"  Clarification Questions:")
            for j, question in enumerate(ambiguity.clarification_questions, 1):
                print(f"    {j}. {question}")
        
        if ambiguity.suggested_interpretations:
            print(f"  Suggested Interpretations:")
            for j, interpretation in enumerate(ambiguity.suggested_interpretations, 1):
                print(f"    {j}. {interpretation}")
        
        # Test language detection
        language_result = enhancer.detect_language(query)
        print(f"\nLanguage Detection:")
        print(f"  Detected Language: {language_result.detected_language}")
        print(f"  Confidence: {language_result.confidence:.2f}")
        
        # Generate clarification questions
        clarifications = enhancer.generate_clarification_questions(query, ambiguity)
        if clarifications:
            print(f"\nGenerated Clarification Questions:")
            for j, clarification in enumerate(clarifications, 1):
                print(f"  {j}. [{clarification.question_type}] {clarification.question}")
                print(f"     Priority: {clarification.priority}")


def demonstrate_vocabulary_management():
    """Demonstrate vocabulary management features."""
    
    print_separator("Vocabulary Management Demo")
    
    enhancer = QueryEnhancer()
    
    print("Technical Terms Sample:")
    sample_terms = list(enhancer.technical_terms)[:10]
    for i, term in enumerate(sample_terms, 1):
        print(f"  {i}. {term}")
    
    print(f"\nTotal Technical Terms: {len(enhancer.technical_terms)}")
    
    print("\nSynonym Dictionary Sample:")
    sample_synonyms = list(enhancer.synonyms.items())[:5]
    for term, synonym_entry in sample_synonyms:
        print(f"  {term}: {synonym_entry.synonyms}")
    
    print(f"\nTotal Synonym Entries: {len(enhancer.synonyms)}")
    
    print("\nCommon Misspellings Sample:")
    sample_misspellings = list(enhancer.common_misspellings.items())[:5]
    for wrong, correct in sample_misspellings:
        print(f"  {wrong} → {correct}")
    
    print(f"\nTotal Misspelling Corrections: {len(enhancer.common_misspellings)}")


def demonstrate_spell_correction():
    """Demonstrate spell correction capabilities."""
    
    print_separator("Spell Correction Demo")
    
    enhancer = QueryEnhancer()
    
    test_queries_with_errors = [
        # French spelling errors
        "Qu'est-ce qu'un algorythme?",
        "Comment fonctionne le chifrement?",
        "Expliquer la gestion de bande passante",
        "Qu'est-ce que le protocoll de comunication?",
        "Définir les techniques de modualtion",
        # English spelling errors
        "What is an algoritm?",
        "How does encription work?",
        "Explain bandwith management"
    ]
    
    for i, query in enumerate(test_queries_with_errors, 1):
        print(f"\n{i}. Original: '{query}'")
        corrected = enhancer.correct_spelling(query)
        print(f"   Corrected: '{corrected}'")
        
        if query != corrected:
            print(f"   ✓ Corrections applied")
        else:
            print(f"   ✓ No corrections needed")


def main():
    """Main demonstration function."""
    
    print("Query Enhancement Engine Demonstration")
    print("=====================================")
    print("\nThis demo shows the capabilities of the Query Enhancement Engine")
    print("including spell correction, term expansion, ambiguity detection,")
    print("language detection, and clarification question generation.")
    
    try:
        # Run demonstrations
        demonstrate_query_enhancement()
        demonstrate_vocabulary_management()
        demonstrate_spell_correction()
        
        print_separator("Demo Complete")
        print("The Query Enhancement Engine successfully demonstrated:")
        print("✓ Query spell correction and normalization")
        print("✓ Term expansion with synonyms")
        print("✓ Intent detection (factual, procedural, comparative, etc.)")
        print("✓ Ambiguity detection and scoring")
        print("✓ Multi-language support (English, French, Arabic)")
        print("✓ Context dependency detection")
        print("✓ Clarification question generation")
        print("✓ Filter extraction from queries")
        print("✓ Vocabulary management")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
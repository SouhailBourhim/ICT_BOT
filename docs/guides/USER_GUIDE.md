# RAG System User Guide

Welcome to the RAG (Retrieval-Augmented Generation) Educational Assistant System! This guide will help you understand and effectively use the system for your Smart ICT studies at INPT.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Document Management](#document-management)
5. [Query Techniques](#query-techniques)
6. [Understanding Responses](#understanding-responses)
7. [Troubleshooting](#troubleshooting)
8. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### Accessing the System

1. **Web Interface**: Open your browser and navigate to the system URL (typically `http://localhost:8501` for local installations)
2. **First Time Setup**: The system will guide you through initial setup if needed
3. **Login**: If authentication is enabled, log in with your credentials

### System Overview

The RAG system is designed to help you with your Smart ICT coursework by:
- Answering questions about course materials
- Providing detailed explanations with source citations
- Maintaining conversation context for follow-up questions
- Supporting multiple languages (French and English)
- Offering advanced search and filtering capabilities

## Basic Usage

### Asking Your First Question

1. **Simple Questions**: Start with straightforward questions
   ```
   What is wireless communication?
   Explain path loss in wireless systems
   How does QPSK modulation work?
   ```

2. **Getting Started**: The system works best with specific, well-formed questions
   ```
   ✅ Good: "What is the formula for calculating path loss in free space?"
   ❌ Avoid: "Tell me about wireless stuff"
   ```

### Understanding the Interface

#### Main Chat Interface
- **Input Box**: Type your questions here
- **Send Button**: Click to submit your question
- **Chat History**: Previous questions and answers are displayed above
- **Clear Button**: Start a new conversation

#### Response Elements
- **Answer Text**: The main response to your question
- **Source Citations**: References to specific documents and page numbers
- **Confidence Score**: Indicates how confident the system is in its answer
- **Related Topics**: Suggestions for follow-up questions

### Basic Query Examples

```
# Course Content Questions
"What are the main types of wireless communication systems?"
"Explain the difference between TDMA and CDMA"
"How do you calculate signal-to-noise ratio?"

# Mathematical Formulas
"Show me the path loss formula"
"What is the Shannon capacity formula?"
"How do you calculate bit error rate for QPSK?"

# Conceptual Questions
"Why is diversity important in wireless communications?"
"What causes fading in wireless channels?"
"How does OFDM reduce intersymbol interference?"
```

## Advanced Features

### Conversation Context

The system remembers your conversation history, allowing for natural follow-up questions:

```
You: "What is MIMO?"
System: [Explains MIMO technology...]

You: "How many antennas does it typically use?"
System: [Understands "it" refers to MIMO and provides antenna information...]

You: "What are the advantages?"
System: [Lists MIMO advantages, maintaining context...]
```

### Multi-Language Support

The system supports both French and English:

```
# English
"What is the difference between analog and digital modulation?"

# French
"Quelle est la différence entre la modulation analogique et numérique?"

# Mixed (the system will respond in the language of your question)
"Explain 'modulation numérique' in English"
```

### Advanced Query Techniques

#### 1. Specific Document Queries
```
"According to the wireless communications textbook, what is path loss?"
"Find information about OFDM in Chapter 3"
"What does the course syllabus say about exam topics?"
```

#### 2. Comparative Questions
```
"Compare QPSK and 16-QAM modulation schemes"
"What are the differences between Rayleigh and Rician fading?"
"Compare the advantages of TDMA vs CDMA"
```

#### 3. Mathematical Problem Solving
```
"Calculate the path loss for a signal at 2.4 GHz over 100 meters"
"If SNR is 20 dB, what is the channel capacity for a 1 MHz bandwidth?"
"Solve for the bit error rate with the given parameters"
```

#### 4. Conceptual Explanations
```
"Explain how diversity techniques improve wireless communication"
"Why is channel coding important in digital communications?"
"Describe the process of digital signal demodulation"
```

### Filtering and Search Options

#### Document Type Filters
- **PDFs**: Course textbooks and lecture slides
- **Exercises**: Problem sets and solutions
- **Syllabus**: Course outline and requirements

#### Course Module Filters
- **Fundamentals**: Basic wireless communication concepts
- **Modulation**: Digital and analog modulation techniques
- **Channel Models**: Fading, path loss, and channel characteristics
- **Advanced Topics**: MIMO, OFDM, and modern techniques

#### Difficulty Level Filters
- **Beginner**: Basic concepts and definitions
- **Intermediate**: Detailed explanations and applications
- **Advanced**: Complex topics and research-level content

## Document Management

### Supported Document Types

The system can process:
- **PDF Files**: Textbooks, lecture slides, research papers
- **Text Files**: Notes, summaries, code examples
- **Word Documents**: Reports, assignments, documentation

### Document Organization

Documents are automatically organized by:
- **Course Module**: Based on content analysis
- **Document Type**: Textbook, slides, exercises, etc.
- **Difficulty Level**: Automatically assessed
- **Language**: French, English, or multilingual
- **Topics**: Key concepts and subjects covered

### Adding New Documents

If you have administrator access:
1. Place documents in the `data/` directory
2. Run the ingestion script: `python3 ingest_enhanced.py`
3. The system will automatically process and index the new content

## Query Techniques

### Effective Question Formulation

#### 1. Be Specific
```
✅ Good: "What is the bit error rate formula for QPSK in AWGN channel?"
❌ Vague: "Tell me about errors in communication"
```

#### 2. Use Technical Terms
```
✅ Good: "Explain intersymbol interference in digital communications"
❌ Unclear: "Why do signals interfere with each other?"
```

#### 3. Ask for Examples
```
"Give me an example of frequency selective fading"
"Show me how to calculate path loss with a numerical example"
"Provide a practical application of diversity techniques"
```

#### 4. Request Step-by-Step Explanations
```
"Step by step, how do you demodulate a QPSK signal?"
"Walk me through the process of channel equalization"
"Explain the OFDM transmission process step by step"
```

### Question Types and Examples

#### Definitional Questions
```
"What is adaptive equalization?"
"Define symbol error rate"
"What does SINR stand for and what does it measure?"
```

#### Procedural Questions
```
"How do you implement a matched filter?"
"What are the steps to design a convolutional code?"
"How do you measure channel capacity in practice?"
```

#### Analytical Questions
```
"Why is OFDM more robust against multipath fading?"
"What factors affect the performance of a MIMO system?"
"How does antenna diversity improve system reliability?"
```

#### Problem-Solving Questions
```
"Calculate the required SNR for a BER of 10^-6 in QPSK"
"Design a communication system for a 10 km link"
"Optimize the parameters for maximum channel capacity"
```

## Understanding Responses

### Response Components

#### 1. Main Answer
- Clear, comprehensive explanation
- Technical accuracy with appropriate detail level
- Structured information with logical flow

#### 2. Source Citations
- Document name and page number
- Section or chapter references
- Multiple sources when applicable

#### 3. Confidence Indicators
- **High (>80%)**: Very reliable information
- **Medium (60-80%)**: Good information, may need verification
- **Low (<60%)**: Uncertain, consult original sources

#### 4. Related Information
- Cross-references to related topics
- Suggestions for further reading
- Links to relevant exercises or examples

### Interpreting Citations

Citations appear in this format:
```
[Source: Wireless_Communications_Goldsmith_Ch1.pdf, Page 15, Section 1.3]
[Source: Rayleigh_Channels_Part1.pdf, Page 8]
[Source: Course_Exercises_Serie_2.pdf, Problem 3]
```

### Quality Indicators

Look for these quality indicators in responses:
- **Multiple Sources**: Information confirmed across documents
- **Specific References**: Exact page numbers and sections
- **Mathematical Formulas**: Properly formatted equations
- **Examples**: Concrete illustrations of concepts
- **Diagrams**: References to figures and illustrations

## Troubleshooting

### Common Issues and Solutions

#### 1. No Results Found
**Problem**: "I'm sorry, I couldn't find relevant information..."

**Solutions**:
- Try rephrasing your question with different terms
- Use more general terms initially, then ask follow-up questions
- Check spelling of technical terms
- Try asking in a different language

#### 2. Irrelevant Responses
**Problem**: The answer doesn't match your question

**Solutions**:
- Be more specific in your question
- Include context about what you're looking for
- Use technical terminology from your course materials
- Ask follow-up questions to clarify

#### 3. Incomplete Answers
**Problem**: The response seems cut off or incomplete

**Solutions**:
- Ask for more details: "Can you elaborate on..."
- Request specific aspects: "Tell me more about the mathematical derivation"
- Ask for examples: "Can you provide a practical example?"

#### 4. Low Confidence Responses
**Problem**: System indicates low confidence in the answer

**Solutions**:
- Cross-reference with original course materials
- Ask for alternative explanations
- Request multiple perspectives on the topic
- Consult with instructors for verification

### Getting Better Results

#### 1. Use Course Vocabulary
```
✅ Use: "QPSK", "path loss", "diversity gain"
❌ Avoid: "that modulation thing", "signal weakening"
```

#### 2. Provide Context
```
✅ Good: "In the context of OFDM systems, what is the cyclic prefix?"
❌ Vague: "What is cyclic prefix?"
```

#### 3. Ask Follow-Up Questions
```
Initial: "What is channel coding?"
Follow-up: "How does it differ from source coding?"
Follow-up: "Can you give me an example of a channel code?"
```

## Tips and Best Practices

### Maximizing Learning Effectiveness

#### 1. Start Broad, Then Narrow
```
1. "What is wireless communication?" (broad overview)
2. "What are the main challenges in wireless systems?" (specific aspects)
3. "How does fading affect signal quality?" (detailed topic)
```

#### 2. Connect Concepts
```
"How does the concept of path loss relate to link budget calculations?"
"What is the relationship between bandwidth and channel capacity?"
"How do modulation and coding work together in digital communications?"
```

#### 3. Practice with Examples
```
"Give me a numerical example of path loss calculation"
"Show me how to apply the Shannon formula with specific values"
"Walk through a complete link budget analysis"
```

#### 4. Verify Understanding
```
"Can you explain this concept in simpler terms?"
"What would happen if we changed this parameter?"
"How would this apply in a real-world scenario?"
```

### Study Strategies

#### 1. Topic Exploration
- Start with fundamental concepts
- Build up to complex topics gradually
- Ask for relationships between concepts
- Request practical applications

#### 2. Problem Solving
- Ask for step-by-step solutions
- Request explanation of each step
- Try variations of problems
- Ask about common mistakes

#### 3. Exam Preparation
- Review key formulas and their applications
- Ask for typical exam questions on topics
- Practice with different problem types
- Clarify confusing concepts

#### 4. Research Support
- Explore advanced topics beyond basic coursework
- Ask for current research directions
- Request references to additional materials
- Investigate practical implementations

### Language Learning Support

#### For French Students Learning Technical English
```
"What is the English term for 'modulation d'amplitude'?"
"Explain 'path loss' and provide the French equivalent"
"What are the key English technical terms for wireless communication?"
```

#### For English Students Learning French Technical Terms
```
"What is 'wireless communication' in French?"
"Explain the French terminology for modulation techniques"
"Provide French technical vocabulary for this topic"
```

### Collaboration and Discussion

#### Preparing for Group Work
```
"What are the main points I should understand about MIMO for our group project?"
"Can you summarize the key concepts for our presentation on OFDM?"
"What are the most important formulas for our assignment on channel capacity?"
```

#### Discussion Preparation
```
"What are the current debates about 5G technology?"
"What are the advantages and disadvantages of different modulation schemes?"
"What are the open research questions in wireless communications?"
```

## Advanced Usage Scenarios

### Research and Projects

#### Literature Review Support
```
"What are the main research areas in wireless communications?"
"Summarize the key developments in MIMO technology"
"What are the current challenges in 5G implementation?"
```

#### Technical Writing Support
```
"How should I explain path loss in a technical report?"
"What is the standard way to present BER performance results?"
"How do I properly cite wireless communication standards?"
```

### Exam and Assignment Help

#### Concept Review
```
"Quiz me on the key concepts in Chapter 3"
"What are the most important formulas for the midterm exam?"
"Explain the concepts I need to know for the final project"
```

#### Problem-Solving Practice
```
"Give me practice problems on channel capacity calculations"
"Help me understand this homework problem step by step"
"What approach should I use for this type of analysis?"
```

Remember: The RAG system is designed to enhance your learning experience, not replace studying. Use it as a powerful tool to deepen your understanding, clarify concepts, and explore topics in greater detail. Always verify important information with your course materials and instructors.
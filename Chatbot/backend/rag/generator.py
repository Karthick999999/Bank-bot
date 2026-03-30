"""Response generator - local template-based + optional LLM enhancement."""
import json
import re
import random

from backend.config import Config

# Greeting responses
GREETING_RESPONSES = [
    "Hello! I'm BankBot, your AI-powered banking knowledge assistant. I can help you with banking policies, procedures, compliance requirements, product information, and much more. How can I assist you today?",
    "Hi there! Welcome to the Banking Knowledge Assistant. I'm here to help you find information about banking operations, compliance guidelines, product details, and SOPs. What would you like to know?",
    "Greetings! I'm your intelligent banking knowledge companion. Ask me anything about banking policies, regulatory guidelines, account operations, loans, digital banking, or compliance matters.",
]

FAREWELL_RESPONSES = [
    "Thank you for using the Banking Knowledge Assistant! If you have more questions, feel free to ask anytime. Have a great day!",
    "Goodbye! Remember, I'm always here to help with your banking knowledge queries. Stay compliant!",
]

HELP_RESPONSE = """I'm the **Banking Knowledge Chatbot** — your AI assistant for banking operations and compliance.

Here's what I can help you with:

🏦 **Account Operations** — Account opening, KYC, closure, joint accounts, NRI banking
💰 **Loan Products** — Home loans, personal loans, business loans, EMI, NPA management
📋 **Compliance & Regulatory** — RBI guidelines, AML/KYC, FEMA, Basel III, PSL norms
💳 **Card Services** — Credit/debit cards, disputes, chargebacks, fraud prevention
📱 **Digital Banking** — UPI, NEFT, RTGS, IMPS, internet/mobile banking security
🏢 **Treasury & Trade Finance** — Letters of credit, bank guarantees, forex
⚠️ **Risk Management** — Credit risk, market risk, operational risk, cyber security
📞 **Customer Service** — Complaint handling, ombudsman, grievance redressal
👤 **HR & Onboarding** — Employee guidelines, training, code of conduct

Just type your question and I'll provide accurate answers with source references!"""

NO_RESULTS_RESPONSE = """I'm sorry, I couldn't find specific information related to your query in my knowledge base. 

Here are some suggestions:
- Try rephrasing your question with more specific banking terms
- Ask about a specific policy, procedure, or regulation
- Use keywords like "KYC", "loan", "compliance", "account", "UPI", etc.

If this is an urgent matter, please contact your supervisor or the relevant department directly."""


def generate_response(query, retrieved_docs, categorization, chat_history=None):
    """Generate response based on retrieved documents."""
    category = categorization.get("category", "general")
    
    # Handle greetings
    if category == "greeting":
        query_lower = query.lower()
        if any(w in query_lower for w in ["bye", "goodbye", "see you"]):
            return {"response": random.choice(FAREWELL_RESPONSES), "sources": [], "confidence": 0.95, "category": "greeting"}
        if any(w in query_lower for w in ["help", "what can you do", "who are you"]):
            return {"response": HELP_RESPONSE, "sources": [], "confidence": 0.95, "category": "greeting"}
        if any(w in query_lower for w in ["thanks", "thank you"]):
            return {"response": "You're welcome! If you have any more questions about banking policies or procedures, feel free to ask.", "sources": [], "confidence": 0.95, "category": "greeting"}
        return {"response": random.choice(GREETING_RESPONSES), "sources": [], "confidence": 0.95, "category": "greeting"}
    
    # No results found
    if not retrieved_docs:
        return {"response": NO_RESULTS_RESPONSE, "sources": [], "confidence": 0.1, "category": category}
    
    # Try LLM generation first
    llm_response = _try_llm_generation(query, retrieved_docs, chat_history)
    if llm_response:
        return llm_response
    
    # Local template-based generation
    return _local_generation(query, retrieved_docs, categorization)


def _try_llm_generation(query, retrieved_docs, chat_history=None):
    """Try to generate response using LLM (Gemini or OpenAI)."""
    if Config.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            
            context = "\n\n".join([
                f"[Source: {doc['title']} ({doc['doc_id']})]\n{doc['content']}"
                for doc in retrieved_docs[:4]
            ])
            
            history_text = ""
            if chat_history:
                history_text = "\n".join([
                    f"{msg['role'].upper()}: {msg['content'][:200]}"
                    for msg in chat_history[-4:]
                ])
                history_text = f"\nRecent Conversation:\n{history_text}\n"
            
            prompt = f"""You are BankBot, a professional banking knowledge assistant. Answer the user's question ONLY using the provided context. Be accurate, comprehensive, and cite your sources.

Context Documents:
{context}
{history_text}
User Question: {query}

Instructions:
- Answer based ONLY on the provided context
- Be specific with numbers, rates, and procedures
- Use bullet points for steps and lists
- Mention the source document ID in your answer
- If the context doesn't fully answer the question, say what you know and note limitations
- Keep the tone professional but friendly"""
            
            response = model.generate_content(prompt)
            sources = [{"title": d["title"], "doc_id": d["doc_id"], "category": d["category"], "similarity": d["similarity"]} for d in retrieved_docs[:4]]
            
            return {
                "response": response.text,
                "sources": sources,
                "confidence": max(d["similarity"] for d in retrieved_docs[:3]),
                "category": retrieved_docs[0]["category"],
                "llm_used": True,
            }
        except Exception as e:
            print(f"[Generator] LLM error: {e}")
            return None
    return None


def _local_generation(query, retrieved_docs, categorization):
    """Generate response using local template-based approach."""
    top_doc = retrieved_docs[0]
    confidence = top_doc["similarity"]
    
    # Build response from top results
    response_parts = []
    sources = []
    
    # Main answer from top document
    content = top_doc["content"]
    title = top_doc["title"]
    
    # Extract the most relevant portion
    response_parts.append(f"### {title}\n")
    
    # Format content nicely
    formatted = _format_content(content, query)
    response_parts.append(formatted)
    
    # Add supplementary info from other results
    if len(retrieved_docs) > 1 and retrieved_docs[1]["similarity"] > 0.35:
        response_parts.append(f"\n\n### Related: {retrieved_docs[1]['title']}\n")
        supplementary = _format_content(retrieved_docs[1]["content"], query)
        # Limit supplementary content
        if len(supplementary) > 500:
            supplementary = supplementary[:500] + "..."
        response_parts.append(supplementary)
    
    # Build sources list
    for doc in retrieved_docs[:3]:
        sources.append({
            "title": doc["title"],
            "doc_id": doc["doc_id"],
            "category": doc["category"],
            "similarity": doc["similarity"],
        })
    
    response = "\n".join(response_parts)
    
    # Add confidence note if low
    if confidence < 0.4:
        response += "\n\n> ⚠️ *This response has moderate confidence. Please verify with your department's latest guidelines.*"
    
    return {
        "response": response,
        "sources": sources,
        "confidence": round(confidence, 2),
        "category": categorization.get("category", "general"),
    }


def _format_content(content, query):
    """Format raw content into readable response."""
    # Split by common delimiters
    content = content.strip()
    
    # Convert Step patterns to numbered list
    content = re.sub(r'Step (\d+):', r'\n**Step \1:**', content)
    
    # Convert key-value patterns
    content = re.sub(r'(\w[\w\s]+?):\s*(?=\S)', r'\n- **\1:** ', content)
    
    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

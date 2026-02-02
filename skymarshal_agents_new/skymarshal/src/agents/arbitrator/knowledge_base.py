"""AWS Bedrock Knowledge Base integration for arbitrator

This module provides access to operational documentation including:
- Process Manual - Network Operations
- Operation Control Manual
- Standard Operating Procedures (SOPs)
- Disruption Management Protocols
- Recovery Workflows and Decision Trees

The knowledge base helps the arbitrator make decisions aligned with
airline operational standards, just like a duty manager would reference
these documents in real-world scenarios.
"""

import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Default Knowledge Base ID for SkyMarshal operational documentation
DEFAULT_KNOWLEDGE_BASE_ID = "UDONMVCXEW"


class KnowledgeBaseClient:
    """
    Client for querying AWS Bedrock Knowledge Base containing operational documentation.
    
    Provides access to:
    - Network Operations Process Manual
    - Operation Control Manual (OCM)
    - Disruption Management Procedures
    - Recovery Protocols and Workflows
    - Decision-making Guidelines
    
    This enables the arbitrator to make decisions consistent with
    established airline operational standards and procedures.
    """
    
    def __init__(self, knowledge_base_id: Optional[str] = None):
        """
        Initialize Knowledge Base client.
        
        Args:
            knowledge_base_id: Bedrock Knowledge Base ID (optional)
                              If None, uses DEFAULT_KNOWLEDGE_BASE_ID or env variable
        """
        self.knowledge_base_id = knowledge_base_id or os.getenv("KNOWLEDGE_BASE_ID", DEFAULT_KNOWLEDGE_BASE_ID)
        self.enabled = bool(self.knowledge_base_id)
        
        if self.enabled:
            try:
                import boto3
                self.client = boto3.client('bedrock-agent-runtime')
                logger.info(f"Knowledge Base client initialized: kb_id={self.knowledge_base_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Knowledge Base client: {e}")
                self.enabled = False
                self.client = None
        else:
            logger.info("Knowledge Base not configured - using LLM-only reasoning")
            self.client = None
    
    async def query_operational_procedures(
        self,
        disruption_scenario: str,
        binding_constraints: List[str],
        agent_recommendations: Dict[str, Any],
        max_results: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Query Knowledge Base for relevant operational procedures and guidelines.
        
        Searches the knowledge base for:
        - Standard Operating Procedures (SOPs) for the disruption type
        - Decision-making protocols from Operation Control Manual
        - Recovery workflows from Network Operations Process Manual
        - Regulatory compliance guidelines
        
        Args:
            disruption_scenario: Description of the disruption scenario
            binding_constraints: Safety constraints that must be satisfied
            agent_recommendations: Summary of recommendations from all agents
            max_results: Maximum number of documents to retrieve
            
        Returns:
            dict: Operational guidance with source citations
        """
        if not self.enabled:
            logger.warning("Knowledge Base not enabled - skipping operational procedures query")
            return None
        
        try:
            # Build a comprehensive query for operational procedures
            constraints_text = "; ".join(binding_constraints[:5]) if binding_constraints else "none specified"
            
            # Extract key issues from agent recommendations
            key_issues = self._extract_key_issues(agent_recommendations)
            
            query = f"""Find relevant operational procedures and guidelines for this airline disruption scenario:

SCENARIO: {disruption_scenario}

SAFETY CONSTRAINTS TO SATISFY:
{constraints_text}

KEY ISSUES IDENTIFIED:
{key_issues}

Please provide:
1. Relevant Standard Operating Procedures (SOPs) for handling this type of disruption
2. Decision-making protocols from the Operation Control Manual
3. Recovery workflow steps from the Network Operations Process Manual
4. Any regulatory compliance requirements that apply
5. Escalation procedures if applicable"""

            logger.info(f"Querying knowledge base for operational procedures...")
            logger.debug(f"Query: {query[:200]}...")
            
            # Use retrieve API to get relevant documents
            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            
            # Process results into structured procedures
            procedures = []
            applicable_protocols = []
            
            for item in response.get('retrievalResults', []):
                content = item.get('content', {}).get('text', '')
                score = item.get('score', 0.0)
                source = item.get('location', {}).get('s3Location', {}).get('uri', 'Unknown')
                
                if content:
                    doc_type = self._identify_document_type(source, content)
                    procedures.append({
                        'content': content,
                        'source': source,
                        'relevance_score': score,
                        'document_type': doc_type
                    })
                    
                    # Extract protocol names mentioned in the content
                    protocols = self._extract_protocol_names(content)
                    applicable_protocols.extend(protocols)
            
            # Remove duplicate protocols
            applicable_protocols = list(set(applicable_protocols))
            
            # Generate decision guidance summary
            decision_guidance = self._synthesize_decision_guidance(procedures, binding_constraints)
            
            from datetime import datetime
            result = {
                'procedures': procedures,
                'decision_guidance': decision_guidance,
                'applicable_protocols': applicable_protocols,
                'query': query,
                'timestamp': datetime.utcnow().isoformat(),
                'documents_found': len(procedures)
            }
            
            logger.info(f"Operational procedures query successful: {len(procedures)} documents found")
            return result
            
        except Exception as e:
            logger.error(f"Operational procedures query failed: {e}")
            logger.exception("Full traceback:")
            return None

    
    async def query_recovery_workflow(
        self,
        disruption_type: str,
        constraints: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Query for specific recovery workflow steps for a disruption type.
        
        Args:
            disruption_type: Type of disruption (e.g., "crew shortage", "mechanical delay")
            constraints: Constraints that must be satisfied
            
        Returns:
            dict: Recovery workflow with steps and decision points
        """
        if not self.enabled:
            return None
        
        try:
            query = f"""What is the standard recovery workflow for handling a {disruption_type}?

Include:
- Step-by-step recovery procedure
- Decision points and criteria
- Escalation triggers
- Communication requirements
- Documentation requirements

Constraints to consider: {', '.join(constraints[:3]) if constraints else 'standard safety requirements'}"""

            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {'numberOfResults': 3}
                }
            )
            
            workflows = []
            for item in response.get('retrievalResults', []):
                content = item.get('content', {}).get('text', '')
                source = item.get('location', {}).get('s3Location', {}).get('uri', 'Unknown')
                if content:
                    workflows.append({
                        'workflow_steps': content,
                        'source': source,
                        'relevance': item.get('score', 0.0)
                    })
            
            from datetime import datetime
            return {
                'workflows': workflows,
                'disruption_type': disruption_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Recovery workflow query failed: {e}")
            return None
    
    async def query_decision_criteria(
        self,
        decision_type: str,
        options: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Query for decision-making criteria from operational manuals.
        
        Args:
            decision_type: Type of decision (e.g., "delay vs cancel", "crew swap vs rest")
            options: Available options to choose from
            
        Returns:
            dict: Decision criteria and guidelines
        """
        if not self.enabled:
            return None
        
        try:
            options_text = ", ".join(options) if options else "available recovery options"
            
            query = f"""What are the decision-making criteria for choosing between {options_text} when handling a {decision_type} decision?

Include:
- Priority factors to consider
- Cost-benefit analysis guidelines
- Safety vs operational trade-off rules
- Passenger impact considerations
- Network impact considerations"""

            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {'numberOfResults': 3}
                }
            )
            
            criteria = []
            for item in response.get('retrievalResults', []):
                content = item.get('content', {}).get('text', '')
                if content:
                    criteria.append({
                        'guidance': content,
                        'source': item.get('location', {}).get('s3Location', {}).get('uri', 'Unknown'),
                        'relevance': item.get('score', 0.0)
                    })
            
            from datetime import datetime
            return {
                'criteria': criteria,
                'decision_type': decision_type,
                'options_evaluated': options,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Decision criteria query failed: {e}")
            return None

    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_key_issues(self, agent_recommendations: Dict[str, Any]) -> str:
        """
        Extract key issues from agent recommendations for KB query.
        
        Args:
            agent_recommendations: Dict of agent responses
            
        Returns:
            str: Formatted key issues text
        """
        issues = []
        
        for agent_name, response in agent_recommendations.items():
            if isinstance(response, dict):
                rec = response.get('recommendation', '')
                reasoning = response.get('reasoning', '')
                
                # Extract key points from recommendation
                if rec:
                    issues.append(f"- {agent_name.replace('_', ' ').title()}: {rec[:200]}")
                
                # Check for binding constraints (safety agents)
                constraints = response.get('binding_constraints', [])
                if constraints:
                    for c in constraints[:2]:  # Limit to 2 constraints per agent
                        issues.append(f"  * Constraint: {c}")
        
        return "\n".join(issues) if issues else "No specific issues identified"
    
    def _identify_document_type(self, source: str, content: str) -> str:
        """
        Identify the type of operational document based on source and content.
        
        Args:
            source: S3 URI or document path
            content: Document content text
            
        Returns:
            str: Document type classification
        """
        source_lower = source.lower()
        content_lower = content.lower()[:500]  # Check first 500 chars
        
        # Check source path for document type hints
        if 'sop' in source_lower or 'standard_operating' in source_lower:
            return 'Standard Operating Procedure (SOP)'
        elif 'ocm' in source_lower or 'operation_control' in source_lower:
            return 'Operation Control Manual (OCM)'
        elif 'network_ops' in source_lower or 'network_operations' in source_lower:
            return 'Network Operations Process Manual'
        elif 'regulatory' in source_lower or 'compliance' in source_lower:
            return 'Regulatory Compliance Guidelines'
        elif 'disruption' in source_lower or 'recovery' in source_lower:
            return 'Disruption Management Protocol'
        
        # Check content for document type hints
        if 'standard operating procedure' in content_lower or 'sop' in content_lower:
            return 'Standard Operating Procedure (SOP)'
        elif 'operation control' in content_lower:
            return 'Operation Control Manual (OCM)'
        elif 'workflow' in content_lower or 'process flow' in content_lower:
            return 'Process Workflow Document'
        elif 'decision tree' in content_lower or 'decision criteria' in content_lower:
            return 'Decision Support Document'
        elif 'escalation' in content_lower:
            return 'Escalation Procedure'
        
        return 'Operational Documentation'
    
    def _extract_protocol_names(self, content: str) -> List[str]:
        """
        Extract protocol/procedure names mentioned in the content.
        
        Args:
            content: Document content text
            
        Returns:
            list: Protocol names found in content
        """
        import re
        
        protocols = []
        
        # Common protocol naming patterns
        patterns = [
            r'(?:SOP|Protocol|Procedure)\s*[-:]?\s*([A-Z0-9][-A-Z0-9.]+)',  # SOP-123, Protocol-ABC
            r'(?:Section|Chapter)\s+(\d+(?:\.\d+)?)\s*[-:]?\s*([A-Za-z\s]+)',  # Section 5.2: Crew Rest
            r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(?:Protocol|Procedure|SOP)',  # Crew Rest Protocol
            r'(?:per|following|according to)\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Manual|Guide|Protocol))',  # per the OCM
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Join tuple matches
                    protocol_name = ' '.join(str(m).strip() for m in match if m)
                else:
                    protocol_name = str(match).strip()
                
                if protocol_name and len(protocol_name) > 3:
                    protocols.append(protocol_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_protocols = []
        for p in protocols:
            p_lower = p.lower()
            if p_lower not in seen:
                seen.add(p_lower)
                unique_protocols.append(p)
        
        return unique_protocols[:10]  # Limit to 10 protocols
    
    def _synthesize_decision_guidance(
        self,
        procedures: List[Dict[str, Any]],
        binding_constraints: List[str]
    ) -> str:
        """
        Synthesize decision guidance from retrieved procedures.
        
        Args:
            procedures: List of retrieved procedure documents
            binding_constraints: Safety constraints that must be satisfied
            
        Returns:
            str: Synthesized decision guidance text
        """
        if not procedures:
            return "No specific operational guidance found. Apply standard safety-first principles."
        
        guidance_parts = []
        
        # Group procedures by document type
        by_type = {}
        for proc in procedures:
            doc_type = proc.get('document_type', 'General')
            if doc_type not in by_type:
                by_type[doc_type] = []
            by_type[doc_type].append(proc)
        
        # Build guidance summary
        guidance_parts.append("Based on operational documentation:")
        
        for doc_type, docs in by_type.items():
            guidance_parts.append(f"\n**{doc_type}**:")
            for doc in docs[:2]:  # Limit to 2 docs per type
                content = doc.get('content', '')[:300]  # First 300 chars
                score = doc.get('relevance_score', 0.0)
                if content:
                    guidance_parts.append(f"- (Relevance: {score:.0%}) {content}...")
        
        # Add constraint alignment note
        if binding_constraints:
            guidance_parts.append(f"\nEnsure compliance with {len(binding_constraints)} binding constraint(s).")
        
        return "\n".join(guidance_parts)


# ============================================================================
# Singleton Pattern for Knowledge Base Client
# ============================================================================

_kb_client_instance: Optional[KnowledgeBaseClient] = None


def get_knowledge_base_client(knowledge_base_id: Optional[str] = None) -> KnowledgeBaseClient:
    """
    Get singleton instance of Knowledge Base client.
    
    Creates a single shared instance of the KnowledgeBaseClient to avoid
    creating multiple boto3 clients. Thread-safe for async usage.
    
    Args:
        knowledge_base_id: Optional KB ID override (only used on first call)
        
    Returns:
        KnowledgeBaseClient: Singleton client instance
        
    Example:
        >>> kb = get_knowledge_base_client()
        >>> result = await kb.query_operational_procedures(...)
    """
    global _kb_client_instance
    
    if _kb_client_instance is None:
        _kb_client_instance = KnowledgeBaseClient(knowledge_base_id)
        logger.info(f"Knowledge Base client singleton created: kb_id={_kb_client_instance.knowledge_base_id}")
    
    return _kb_client_instance

"""Optimized prompt models for agent-to-agent communication.

This module provides structured prompt models optimized for machine-to-machine
communication using XML format following Anthropic Claude best practices.

Key principles:
- Use XML tags for structure (Claude trained on XML)
- Be specific and concise - avoid verbose explanations
- Consistent tag naming throughout prompts
- Nest tags hierarchically for complex structures
- Remove human-oriented language for A2A communication
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class OptimizedPrompt(BaseModel):
    """Structured prompt for agent-to-agent communication.
    
    Optimized for Claude models using XML format to minimize token usage
    and maximize parsing efficiency.
    
    Attributes:
        disruption: User's disruption description
        task: Task type (initial_analysis or revision)
        context: Optional Phase 1 results for revision phase
    """
    
    disruption: str = Field(..., description="User's disruption description")
    task: str = Field(..., description="Task type: initial_analysis|revision")
    context: Optional[Dict[str, Any]] = Field(
        None, 
        description="Phase 1 results for revision phase"
    )
    
    def to_xml_phase1(self) -> str:
        """Convert to XML format for Phase 1 (initial analysis).
        
        Phase 1 format is minimal - just disruption and task.
        
        Returns:
            str: XML-formatted prompt
            
        Example:
            >>> prompt = OptimizedPrompt(
            ...     disruption="Flight EY123 delayed 3h",
            ...     task="initial_analysis"
            ... )
            >>> print(prompt.to_xml_phase1())
            <disruption>Flight EY123 delayed 3h</disruption>
            <task>initial_analysis</task>
        """
        xml = f"<disruption>{self.disruption}</disruption>\n"
        xml += f"<task>{self.task}</task>"
        return xml
    
    # Agent name abbreviations for compact XML
    AGENT_ABBREVIATIONS: dict = {
        "crew_compliance": "crew",
        "maintenance": "maint",
        "regulatory": "reg",
        "network": "net",
        "guest_experience": "gx",
        "cargo": "cargo",
        "finance": "fin",
    }

    def to_xml_phase2(self) -> str:
        """Convert to compact XML format for Phase 2 (revision with context).

        Uses abbreviated agent names and inline format to minimize token usage:
        - Agent names shortened (crew_compliance -> crew)
        - Recommendations truncated to 80 chars
        - Constraints inlined with pipe separator
        - Confidence as attribute

        Returns:
            str: Compact XML-formatted prompt with context

        Example:
            >>> prompt = OptimizedPrompt(
            ...     disruption="Flight EY123 delayed 3h",
            ...     task="revision",
            ...     context={
            ...         "crew_compliance": {
            ...             "recommendation": "CREW_CHANGE: Captain exceeds FDP",
            ...             "confidence": 0.95,
            ...             "binding_constraints": ["FDP limit: 13h"]
            ...         }
            ...     }
            ... )
            >>> print(prompt.to_xml_phase2())
            <disruption>Flight EY123 delayed 3h</disruption>
            <task>revision</task>
            <ctx>
              <crew c="0.95">CREW_CHANGE: Captain exceeds FDP|FDP limit: 13h</crew>
            </ctx>
        """
        xml = f"<disruption>{self.disruption}</disruption>\n"
        xml += f"<task>{self.task}</task>\n"

        if self.context:
            xml += "<ctx>\n"
            for agent_name, response in self.context.items():
                # Use abbreviated agent name
                abbrev = self.AGENT_ABBREVIATIONS.get(agent_name, agent_name[:4])

                # Truncate recommendation to 80 chars
                recommendation = response.get("recommendation", "N/A")
                if len(recommendation) > 80:
                    recommendation = recommendation[:77] + "..."

                # Get confidence
                confidence = response.get("confidence", 0.0)

                # Get constraints (max 2, semicolon-separated)
                binding_constraints = response.get("binding_constraints", [])
                constraints_str = "; ".join(binding_constraints[:2]) if binding_constraints else ""

                # Build compact inline format: <abbrev c="conf">rec|constraints</abbrev>
                content = self._escape_xml(recommendation)
                if constraints_str:
                    content += f"|{self._escape_xml(constraints_str)}"

                xml += f'  <{abbrev} c="{confidence:.2f}">{content}</{abbrev}>\n'
            xml += "</ctx>"

        return xml
    
    def to_xml(self) -> str:
        """Convert to XML format based on task type.
        
        Automatically selects Phase 1 or Phase 2 format based on task field.
        
        Returns:
            str: XML-formatted prompt
        """
        if self.task == "initial_analysis":
            return self.to_xml_phase1()
        elif self.task == "revision":
            return self.to_xml_phase2()
        else:
            # Default to Phase 1 format for unknown tasks
            return self.to_xml_phase1()
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            str: XML-escaped text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Escape XML special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        
        return text


class ArbitratorPrompt(BaseModel):
    """Structured prompt for arbitrator.

    Optimized for final decision-making with compact input from both phases.

    Attributes:
        phase1: Initial collation from Phase 1
        phase2: Revised collation from Phase 2
    """

    phase1: Dict[str, Any] = Field(..., description="Phase 1 initial collation")
    phase2: Dict[str, Any] = Field(..., description="Phase 2 revised collation")

    # Agent name abbreviations
    AGENT_ABBREVIATIONS: dict = {
        "crew_compliance": "crew",
        "maintenance": "maint",
        "regulatory": "reg",
        "network": "net",
        "guest_experience": "gx",
        "cargo": "cargo",
        "finance": "fin",
    }

    def to_xml(self) -> str:
        """Convert to compact XML format for arbitrator.

        Uses abbreviated agent names and inline format to minimize token usage
        while preserving key decision-making information.

        Returns:
            str: Compact XML-formatted arbitrator prompt
        """
        xml = "<role>arbitrator</role>\n"
        xml += "<priority>safety_constraints_binding</priority>\n"
        xml += "<input>\n"

        # Add Phase 1 responses (compact)
        xml += "  <p1>\n"
        xml += self._format_phase_responses(self.phase1.get("responses", {}))
        xml += "  </p1>\n"

        # Add Phase 2 responses (compact)
        xml += "  <p2>\n"
        xml += self._format_phase_responses(self.phase2.get("responses", {}))
        xml += "  </p2>\n"

        xml += "</input>\n"
        xml += "<task>resolve_conflicts, final_decision</task>"

        return xml

    def _format_phase_responses(self, responses: Dict[str, Any]) -> str:
        """Format phase responses in compact inline format."""
        xml = ""
        for agent_name, response in responses.items():
            abbrev = self.AGENT_ABBREVIATIONS.get(agent_name, agent_name[:4])

            # Truncate recommendation to 100 chars
            recommendation = response.get("recommendation", "N/A")
            if len(recommendation) > 100:
                recommendation = recommendation[:97] + "..."

            confidence = response.get("confidence", 0.0)

            # Get constraints (max 3)
            binding_constraints = response.get("binding_constraints", [])
            constraints_str = "; ".join(binding_constraints[:3]) if binding_constraints else ""

            # Compact format: <abbrev c="conf">rec|constraints</abbrev>
            content = self._escape_xml(recommendation)
            if constraints_str:
                content += f"|{self._escape_xml(constraints_str)}"

            xml += f'    <{abbrev} c="{confidence:.2f}">{content}</{abbrev}>\n'

        return xml
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            str: XML-escaped text
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Escape XML special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        
        return text

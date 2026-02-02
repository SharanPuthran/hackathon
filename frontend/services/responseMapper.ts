/**
 * Response Mapper Module
 * 
 * Transforms API responses into UI data structures for the frontend components.
 */

import { Assessment, AgentResult, Recommendation } from './api';

// Import types from components
export type AgentType =
    | 'Maintenance'
    | 'Regulatory'
    | 'Crew_Compliance'
    | 'Network'
    | 'Guest_Experience'
    | 'Cargo'
    | 'Finance'
    | 'Arbitrator';

export interface MessageData {
    id: string;
    agent: AgentType;
    safetyAnalysis?: string;
    businessImpact?: string;
    crossImpactAnalysis?: string;
    isCrossImpactRound?: boolean;
    isDecision?: boolean;
    solutionTitle?: string;
}

export interface Solution {
    id: string;
    title: string;
    description: string;
    impact: 'low' | 'medium' | 'high';
    cost: string;
    recommended: boolean;
}

/**
 * Response Mapper for transforming API responses to UI data structures
 */
export class ResponseMapper {
    /**
     * Map agent name from API format to UI format
     */
    private static mapAgentName(apiName: string): AgentType {
        // API uses lowercase with underscores, UI uses PascalCase with underscores
        const nameMap: Record<string, AgentType> = {
            'maintenance': 'Maintenance',
            'regulatory': 'Regulatory',
            'crew_compliance': 'Crew_Compliance',
            'network': 'Network',
            'guest_experience': 'Guest_Experience',
            'cargo': 'Cargo',
            'finance': 'Finance',
            'arbitrator': 'Arbitrator',
        };

        const normalized = apiName.toLowerCase().replace(/\s+/g, '_');
        return nameMap[normalized] || 'Maintenance'; // Default fallback
    }

    /**
     * Map a single agent result to MessageData
     */
    private static mapAgentResult(
        agentName: string,
        result: AgentResult,
        messageId: string
    ): MessageData {
        return {
            id: messageId,
            agent: this.mapAgentName(agentName),
            safetyAnalysis: result.safety_analysis,
            businessImpact: result.business_impact,
        };
    }

    /**
     * Map assessment to array of MessageData objects
     * Creates one message per agent in both safety and business phases
     */
    static mapToMessages(assessment: Assessment): MessageData[] {
        const messages: MessageData[] = [];
        let messageCounter = 0;

        // Map safety phase agents
        if (assessment.safety_phase && assessment.safety_phase.agents) {
            Object.entries(assessment.safety_phase.agents).forEach(([agentName, result]) => {
                messages.push(
                    this.mapAgentResult(
                        agentName,
                        result,
                        `msg-safety-${messageCounter++}-${Date.now()}`
                    )
                );
            });
        }

        // Map business phase agents
        if (assessment.business_phase && assessment.business_phase.agents) {
            Object.entries(assessment.business_phase.agents).forEach(([agentName, result]) => {
                messages.push(
                    this.mapAgentResult(
                        agentName,
                        result,
                        `msg-business-${messageCounter++}-${Date.now()}`
                    )
                );
            });
        }

        return messages;
    }

    /**
     * Map recommendations to Solution objects
     */
    static mapToSolutions(recommendations: Recommendation[]): Solution[] {
        if (!recommendations || !Array.isArray(recommendations)) {
            return [];
        }

        return recommendations.map((rec, index) => ({
            id: rec.id || `sol-${index}`,
            title: rec.title || 'Untitled Solution',
            description: rec.description || 'No description available',
            impact: rec.impact || 'medium',
            cost: rec.cost || 'Cost not specified',
            recommended: rec.recommended || false,
        }));
    }

    /**
     * Extract agent messages and solutions from a complete API response
     */
    static parseResponse(assessment: Assessment): {
        messages: MessageData[];
        solutions: Solution[];
    } {
        return {
            messages: this.mapToMessages(assessment),
            solutions: this.mapToSolutions(assessment.recommendations || []),
        };
    }

    /**
     * Validate that an assessment has the required structure
     */
    static validateAssessment(assessment: any): assessment is Assessment {
        if (!assessment || typeof assessment !== 'object') {
            return false;
        }

        // Check for required phase objects
        if (!assessment.safety_phase || !assessment.business_phase) {
            return false;
        }

        // Check that phases have agents
        if (
            typeof assessment.safety_phase !== 'object' ||
            typeof assessment.business_phase !== 'object'
        ) {
            return false;
        }

        return true;
    }
}

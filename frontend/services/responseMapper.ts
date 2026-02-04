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
    recommendation?: string; // NEW: from agent response
    reasoning?: string; // NEW: from agent response
    data_sources?: string[]; // NEW: from agent response
    status?: string; // NEW: agent status (success/error)
    isCrossImpactRound?: boolean;
    isDecision?: boolean;
    solutionTitle?: string;
}

// Impact type interfaces for structured data
export interface PassengerImpact {
    total_passengers: number;
    connecting_passengers: number;
    delay_minutes: number;
    missed_connections: number;
    compensation_required: boolean;
    passenger_notifications: string;
}

export interface FinancialImpact {
    aircraft_swap_cost: number;
    crew_costs: number;
    passenger_compensation: number;
    rebooking_costs?: number;
    hotel_accommodation?: number;
    total_estimated_cost: number;
    currency: string;
}

export interface NetworkImpact {
    downstream_flights_affected: number;
    rotation_preserved: boolean;
    EY17_connection_protected?: boolean;
    network_propagation: string;
}

// Recovery Plan interfaces
export interface RecoveryStep {
    step_number: number;
    step_name: string;
    description: string;
    responsible_agent: string;
    dependencies: number[];
    estimated_duration: string;
    automation_possible: boolean;
    action_type: string;
    parameters: Record<string, any>;
    success_criteria: string;
    rollback_procedure: string | null;
}

export interface ContingencyPlan {
    trigger: string;
    action: string;
    responsible_agent: string;
}

export interface RecoveryPlan {
    solution_id: number;
    total_steps: number;
    estimated_total_duration: string;
    steps: RecoveryStep[];
    critical_path: number[];
    contingency_plans: ContingencyPlan[];
}

export interface Solution {
    id: string;
    solution_id: number;
    title: string;
    description: string;
    recommendations: string[];
    safety_score: number;
    passenger_score: number;
    network_score: number;
    cost_score: number;
    composite_score: number;
    impact: 'low' | 'medium' | 'high';
    cost: string;
    justification: string;
    reasoning: string;
    passenger_impact: PassengerImpact | string;
    financial_impact: FinancialImpact | string;
    network_impact: NetworkImpact | string;
    safety_compliance?: string;
    pros: string[];
    cons: string[];
    risks: string[];
    confidence: number;
    estimated_duration: string;
    recommended: boolean;
    recovery_plan?: RecoveryPlan;
}

// NEW: Three-phase API response structure interfaces
export interface AuditTrail {
    phase1_initial: Phase1Initial;
    phase2_revision: Phase2Revision;
    phase3_arbitration: Phase3Arbitration;
    user_prompt?: string;
}

export interface Phase1Initial {
    phase: 'initial';
    duration_seconds?: number;
    responses: {
        [agentName: string]: AgentResponse;
    };
    timestamp?: string;
}

export interface Phase2Revision {
    phase: 'revision';
    duration_seconds?: number;
    responses: {
        [agentName: string]: AgentResponse;
    };
    timestamp?: string;
}

export interface Phase3Arbitration {
    phase: 'arbitration';
    duration_seconds?: number;
    solution_options: SolutionOption[];
    recommended_solution_id: number;
    reasoning?: string;
    confidence?: number;
    timestamp?: string;
}

export interface AgentResponse {
    agent_name: string;
    recommendation: string;
    reasoning: string;
    data_sources: string[];
    status: 'success' | 'error' | 'timeout';
    confidence?: number;
    duration_seconds?: number;
    error?: string;
    timestamp?: string;
}

export interface SolutionOption {
    solution_id: number;
    title: string;
    description: string;
    recommendations: string[];
    safety_score: number;
    passenger_score: number;
    network_score: number;
    cost_score: number;
    composite_score: number;
    justification: string;
    reasoning: string;
    passenger_impact: PassengerImpact | string;
    financial_impact: FinancialImpact | string;
    network_impact: NetworkImpact | string;
    safety_compliance?: string;
    pros: string[];
    cons: string[];
    risks: string[];
    estimated_duration?: string;
    confidence?: number;
    recovery_plan?: RecoveryPlan;
}

/**
 * Response Mapper for transforming API responses to UI data structures
 */
export class ResponseMapper {
    /**
     * Agent name mapping from API format to UI format
     */
    private static readonly AGENT_NAME_MAP: Record<string, AgentType> = {
        'crew_compliance': 'Crew_Compliance',
        'maintenance': 'Maintenance',
        'regulatory': 'Regulatory',
        'network': 'Network',
        'guest_experience': 'Guest_Experience',
        'cargo': 'Cargo',
        'finance': 'Finance',
        'arbitrator': 'Arbitrator',
    };

    /**
     * Map agent name from API format to UI format
     */
    private static mapAgentName(apiName: string): AgentType {
        const normalized = apiName.toLowerCase().replace(/\s+/g, '_');
        return this.AGENT_NAME_MAP[normalized] || 'Maintenance'; // Default fallback
    }

    /**
     * Parse phase1_initial responses into MessageData array
     * Extracts agent responses from phase1_initial.responses object
     */
    static parsePhase1(phase1: Phase1Initial): MessageData[] {
        const messages: MessageData[] = [];

        if (!phase1 || !phase1.responses) {
            return messages;
        }

        // Iterate through each agent response
        Object.entries(phase1.responses).forEach(([agentName, response]) => {
            const message: MessageData = {
                id: `phase1-${agentName}-${Date.now()}-${Math.random()}`,
                agent: this.mapAgentName(response.agent_name || agentName),
                recommendation: response.recommendation || '',
                reasoning: response.reasoning || '',
                data_sources: Array.isArray(response.data_sources) ? response.data_sources : [],
                status: response.status || 'success',
                isCrossImpactRound: false,
            };

            messages.push(message);
        });

        return messages;
    }

    /**
     * Parse phase2_revision responses into MessageData array
     * Extracts agent responses from phase2_revision.responses object
     * Marks messages with isCrossImpactRound: true
     */
    static parsePhase2(phase2: Phase2Revision): MessageData[] {
        const messages: MessageData[] = [];

        if (!phase2 || !phase2.responses) {
            return messages;
        }

        // Iterate through each agent response
        Object.entries(phase2.responses).forEach(([agentName, response]) => {
            const message: MessageData = {
                id: `phase2-${agentName}-${Date.now()}-${Math.random()}`,
                agent: this.mapAgentName(response.agent_name || agentName),
                recommendation: response.recommendation || '',
                reasoning: response.reasoning || '',
                data_sources: Array.isArray(response.data_sources) ? response.data_sources : [],
                status: response.status || 'success',
                isCrossImpactRound: true, // Mark as cross-impact round
            };

            messages.push(message);
        });

        return messages;
    }

    /**
     * Derive risk level from scoring properties
     * Average of all scores: >= 75 = low, >= 50 = medium, < 50 = high
     */
    private static deriveRiskLevel(solution: SolutionOption): 'low' | 'medium' | 'high' {
        const scores = [
            solution.safety_score || 0,
            solution.passenger_score || 0,
            solution.network_score || 0,
            solution.cost_score || 0,
        ];

        const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;

        if (avgScore >= 75) return 'low';
        if (avgScore >= 50) return 'medium';
        return 'high';
    }

    /**
     * Parse phase3_arbitration solution options into Solution array
     * Extracts solution_options from phase3_arbitration
     * Derives risk level and marks recommended solution
     */
    static parseSolutions(phase3: Phase3Arbitration): Solution[] {
        const solutions: Solution[] = [];

        if (!phase3 || !Array.isArray(phase3.solution_options)) {
            return solutions;
        }

        const recommendedId = phase3.recommended_solution_id;

        phase3.solution_options.forEach((option) => {
            const solution: Solution = {
                id: `solution-${option.solution_id}`,
                solution_id: option.solution_id || 0,
                title: option.title || 'Untitled Solution',
                description: option.description || '',
                recommendations: Array.isArray(option.recommendations) ? option.recommendations : [],
                safety_score: option.safety_score || 0,
                passenger_score: option.passenger_score || 0,
                network_score: option.network_score || 0,
                cost_score: option.cost_score || 0,
                composite_score: option.composite_score || 0,
                impact: this.deriveRiskLevel(option),
                cost: option.estimated_duration || 'Unknown',
                justification: option.justification || '',
                reasoning: option.reasoning || '',
                passenger_impact: option.passenger_impact || '',
                financial_impact: option.financial_impact || '',
                network_impact: option.network_impact || '',
                safety_compliance: option.safety_compliance || '',
                pros: Array.isArray(option.pros) ? option.pros : [],
                cons: Array.isArray(option.cons) ? option.cons : [],
                risks: Array.isArray(option.risks) ? option.risks : [],
                confidence: option.confidence || 0,
                estimated_duration: option.estimated_duration || 'Unknown',
                recommended: option.solution_id === recommendedId,
                recovery_plan: option.recovery_plan || undefined,
            };

            solutions.push(solution);
        });

        return solutions;
    }

    /**
     * Parse final_decision solution options into Solution array
     * Similar to parseSolutions but reads from final_decision structure
     * This version includes recovery_plan data that's missing in phase3_arbitration
     */
    static parseSolutionsFromFinalDecision(finalDecision: any): Solution[] {
        const solutions: Solution[] = [];

        if (!finalDecision || !Array.isArray(finalDecision.solution_options)) {
            return solutions;
        }

        const recommendedId = finalDecision.recommended_solution_id;

        finalDecision.solution_options.forEach((option: any) => {
            const solution: Solution = {
                id: `solution-${option.solution_id}`,
                solution_id: option.solution_id || 0,
                title: option.title || 'Untitled Solution',
                description: option.description || '',
                recommendations: Array.isArray(option.recommendations) ? option.recommendations : [],
                safety_score: option.safety_score || 0,
                passenger_score: option.passenger_score || 0,
                network_score: option.network_score || 0,
                cost_score: option.cost_score || 0,
                composite_score: option.composite_score || 0,
                impact: this.deriveRiskLevel(option),
                cost: option.estimated_duration || 'Unknown',
                justification: option.justification || '',
                reasoning: option.reasoning || '',
                passenger_impact: option.passenger_impact || '',
                financial_impact: option.financial_impact || '',
                network_impact: option.network_impact || '',
                safety_compliance: option.safety_compliance || '',
                pros: Array.isArray(option.pros) ? option.pros : [],
                cons: Array.isArray(option.cons) ? option.cons : [],
                risks: Array.isArray(option.risks) ? option.risks : [],
                confidence: option.confidence || 0,
                estimated_duration: option.estimated_duration || 'Unknown',
                recommended: option.solution_id === recommendedId,
                recovery_plan: option.recovery_plan || undefined,
            };

            solutions.push(solution);
        });

        return solutions;
    }

    /**
     * Main entry point for parsing three-phase audit trail
     * Calls parsePhase1, parsePhase2, and parseSolutions
     * Returns combined result object with all parsed data
     *
     * @param auditTrail - The audit trail containing phase1, phase2, phase3 data
     * @param finalDecision - Optional final_decision object that contains solution_options with recovery_plan
     */
    static parseAuditTrail(auditTrail: AuditTrail, finalDecision?: any): {
        phase1Messages: MessageData[];
        phase2Messages: MessageData[];
        solutions: Solution[];
        recommendedSolutionId: number | null;
    } {
        // Handle missing audit trail
        if (!auditTrail || typeof auditTrail !== 'object') {
            console.warn('Missing or invalid audit trail');
            return {
                phase1Messages: [],
                phase2Messages: [],
                solutions: [],
                recommendedSolutionId: null,
            };
        }

        console.log('=== ResponseMapper.parseAuditTrail ===');
        console.log('phase1_initial exists:', !!auditTrail.phase1_initial);
        console.log('phase2_revision exists:', !!auditTrail.phase2_revision);
        console.log('phase3_arbitration exists:', !!auditTrail.phase3_arbitration);
        console.log('finalDecision exists:', !!finalDecision);
        console.log('finalDecision.solution_options exists:', !!finalDecision?.solution_options);

        // Parse each phase, handling missing phases gracefully
        const phase1Messages = auditTrail.phase1_initial
            ? this.parsePhase1(auditTrail.phase1_initial)
            : [];

        const phase2Messages = auditTrail.phase2_revision
            ? this.parsePhase2(auditTrail.phase2_revision)
            : [];

        // Prefer finalDecision.solution_options if available (it includes recovery_plan)
        // Fall back to phase3_arbitration.solution_options
        let solutions: Solution[] = [];
        let recommendedSolutionId: number | null = null;

        if (finalDecision?.solution_options && Array.isArray(finalDecision.solution_options)) {
            console.log('Using finalDecision.solution_options (includes recovery_plan)');
            solutions = this.parseSolutionsFromFinalDecision(finalDecision);
            recommendedSolutionId = finalDecision.recommended_solution_id || null;
        } else if (auditTrail.phase3_arbitration) {
            console.log('Using phase3_arbitration.solution_options');
            solutions = this.parseSolutions(auditTrail.phase3_arbitration);
            recommendedSolutionId = auditTrail.phase3_arbitration.recommended_solution_id || null;
        }

        console.log('Parsed phase1Messages:', phase1Messages.length);
        console.log('Parsed phase2Messages:', phase2Messages.length);
        console.log('Parsed solutions:', solutions.length);
        console.log('Recommended solution ID:', recommendedSolutionId);

        return {
            phase1Messages,
            phase2Messages,
            solutions,
            recommendedSolutionId,
        };
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

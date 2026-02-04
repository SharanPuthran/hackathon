#!/usr/bin/env python3
"""
SkyMarshal Architecture Diagram Generator
Generates a visual architecture diagram with proper icons for all tools and services.

Requirements:
    pip install diagrams

Usage:
    python generate_architecture_diagram.py
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.storage import S3
from diagrams.aws.network import APIGateway
from diagrams.aws.management import Cloudwatch
from diagrams.aws.security import IAM
from diagrams.aws.ml import Sagemaker
from diagrams.programming.framework import React
from diagrams.programming.language import Python, TypeScript
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.custom import Custom
import os

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define custom icon paths (we'll use generic icons where custom ones aren't available)
ICON_DIR = os.path.join(SCRIPT_DIR, "icons")

def create_architecture_diagram():
    """Generate the SkyMarshal architecture diagram."""

    graph_attr = {
        "fontsize": "24",
        "fontname": "Helvetica Bold",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "spline",
        "nodesep": "0.8",
        "ranksep": "1.2",
    }

    node_attr = {
        "fontsize": "11",
        "fontname": "Helvetica",
    }

    edge_attr = {
        "fontsize": "10",
        "fontname": "Helvetica",
    }

    with Diagram(
        "SkyMarshal - Multi-Agent Airline Disruption Management",
        filename=os.path.join(SCRIPT_DIR, "skymarshal_architecture"),
        outformat="png",
        show=False,
        direction="TB",
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
    ):

        # Frontend Layer
        with Cluster("Frontend Layer", graph_attr={"bgcolor": "#dbeafe", "style": "rounded"}):
            with Cluster("React Application"):
                react = React("React 19")
                typescript = TypeScript("TypeScript")

            with Cluster("UI Components"):
                landing = Rack("LandingPage")
                orchestration = Rack("OrchestrationView")
                arbitrator_panel = Rack("ArbitratorPanel")

        # API Layer
        with Cluster("AWS Cloud", graph_attr={"bgcolor": "#fff7ed", "style": "rounded"}):

            with Cluster("API Layer", graph_attr={"bgcolor": "#ffedd5"}):
                api_gw = APIGateway("API Gateway")

            with Cluster("Compute Layer", graph_attr={"bgcolor": "#fed7aa"}):
                lambda_async = Lambda("Async Handler")
                lambda_status = Lambda("Status Checker")

            # AgentCore Runtime
            with Cluster("AWS Bedrock AgentCore Runtime", graph_attr={"bgcolor": "#f3e8ff", "style": "rounded"}):

                with Cluster("LangGraph Orchestrator", graph_attr={"bgcolor": "#e9d5ff"}):
                    phase1 = Python("Phase 1\nInitial Analysis")
                    phase2 = Python("Phase 2\nRevision Round")
                    phase3 = Python("Phase 3\nArbitration")

                with Cluster("Safety Agents", graph_attr={"bgcolor": "#dcfce7"}):
                    crew = Python("Crew\nCompliance")
                    maintenance = Python("Maintenance")
                    regulatory = Python("Regulatory")

                with Cluster("Business Agents", graph_attr={"bgcolor": "#fef9c3"}):
                    network = Python("Network")
                    guest_exp = Python("Guest\nExperience")
                    cargo = Python("Cargo")
                    finance = Python("Finance")

                with Cluster("Arbitrator", graph_attr={"bgcolor": "#f3e8ff"}):
                    claude = Sagemaker("Claude Opus 4.5")
                    nova = Sagemaker("Amazon Nova\n(Fallback)")

            # Data Layer
            with Cluster("Data Layer", graph_attr={"bgcolor": "#fee2e2"}):
                dynamodb = Dynamodb("DynamoDB\n40+ Tables")
                s3 = S3("S3\nDecisions & Audits")
                knowledge_base = Sagemaker("Bedrock\nKnowledge Base")

            # Observability
            with Cluster("Observability", graph_attr={"bgcolor": "#f3f4f6"}):
                cloudwatch = Cloudwatch("CloudWatch")
                iam = IAM("IAM")

        # Connections - Main Flow
        react >> Edge(color="#3b82f6", style="bold") >> api_gw
        api_gw >> Edge(color="#f97316", style="bold") >> lambda_async
        lambda_async >> Edge(color="#f97316") >> lambda_status

        # Lambda to Orchestrator
        lambda_async >> Edge(color="#8b5cf6", style="bold") >> phase1

        # Orchestrator Flow
        phase1 >> Edge(color="#8b5cf6") >> phase2
        phase2 >> Edge(color="#8b5cf6") >> phase3

        # Phase 1 to Agents
        phase1 >> Edge(color="#22c55e", style="dashed") >> crew
        phase1 >> Edge(color="#22c55e", style="dashed") >> maintenance
        phase1 >> Edge(color="#22c55e", style="dashed") >> regulatory
        phase1 >> Edge(color="#eab308", style="dashed") >> network
        phase1 >> Edge(color="#eab308", style="dashed") >> guest_exp
        phase1 >> Edge(color="#eab308", style="dashed") >> cargo
        phase1 >> Edge(color="#eab308", style="dashed") >> finance

        # Phase 3 to Arbitrator
        phase3 >> Edge(color="#8b5cf6", style="bold") >> claude
        claude >> Edge(color="#6b7280", style="dashed", label="fallback") >> nova

        # Data connections
        claude >> Edge(color="#ef4444") >> dynamodb
        claude >> Edge(color="#ef4444") >> s3
        claude >> Edge(color="#8b5cf6", style="dashed") >> knowledge_base

        # Observability connections
        lambda_async >> Edge(color="#6b7280", style="dotted") >> cloudwatch
        phase1 >> Edge(color="#6b7280", style="dotted") >> cloudwatch


def create_simplified_diagram():
    """Generate a simplified high-level architecture diagram."""

    graph_attr = {
        "fontsize": "28",
        "fontname": "Helvetica Bold",
        "bgcolor": "white",
        "pad": "0.8",
        "splines": "ortho",
        "nodesep": "1.0",
        "ranksep": "1.5",
    }

    with Diagram(
        "SkyMarshal Architecture Overview",
        filename=os.path.join(SCRIPT_DIR, "skymarshal_architecture_simple"),
        outformat="png",
        show=False,
        direction="TB",
        graph_attr=graph_attr,
    ):

        # User
        user = Rack("User")

        # Frontend
        with Cluster("Frontend", graph_attr={"bgcolor": "#dbeafe"}):
            frontend = React("React + TypeScript\n+ Vite")

        # API
        with Cluster("API Layer", graph_attr={"bgcolor": "#ffedd5"}):
            api = APIGateway("API Gateway")
            lambdas = Lambda("Lambda\n(Async)")

        # Agents
        with Cluster("Bedrock AgentCore", graph_attr={"bgcolor": "#f3e8ff"}):
            with Cluster("LangGraph"):
                orchestrator = Python("Orchestrator\n3 Phases")

            with Cluster("7 Domain Agents"):
                safety = Python("Safety\nAgents (3)")
                business = Python("Business\nAgents (4)")

            with Cluster("Arbitrator"):
                llm = Sagemaker("Claude Opus 4.5")

        # Data
        with Cluster("Data Layer", graph_attr={"bgcolor": "#fee2e2"}):
            db = Dynamodb("DynamoDB")
            storage = S3("S3")

        # Observability
        cw = Cloudwatch("CloudWatch")

        # Flow
        user >> frontend >> api >> lambdas >> orchestrator
        orchestrator >> safety
        orchestrator >> business
        safety >> llm
        business >> llm
        llm >> db
        llm >> storage
        lambdas >> Edge(style="dotted") >> cw


def create_data_flow_diagram():
    """Generate a data flow focused diagram."""

    graph_attr = {
        "fontsize": "24",
        "fontname": "Helvetica Bold",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "LR",
    }

    with Diagram(
        "SkyMarshal Data Flow",
        filename=os.path.join(SCRIPT_DIR, "skymarshal_dataflow"),
        outformat="png",
        show=False,
        direction="LR",
        graph_attr=graph_attr,
    ):

        # Input
        user_input = Rack("Flight\nDisruption\nInput")

        # Processing stages
        with Cluster("Phase 1: Analysis"):
            p1_safety = Python("Safety\nAnalysis")
            p1_business = Python("Business\nAnalysis")

        with Cluster("Phase 2: Revision"):
            p2 = Python("Context-Aware\nRevision")

        with Cluster("Phase 3: Decision"):
            arbitrator = Sagemaker("Claude\nOpus 4.5")

        # Output
        with Cluster("Output"):
            decision = Rack("Final\nDecision")
            scenarios = Rack("Recovery\nScenarios")

        # Storage
        db = Dynamodb("DynamoDB")
        s3 = S3("S3")

        # Flow
        user_input >> p1_safety
        user_input >> p1_business
        p1_safety >> p2
        p1_business >> p2
        p2 >> arbitrator
        arbitrator >> decision
        arbitrator >> scenarios
        arbitrator >> db
        arbitrator >> s3


if __name__ == "__main__":
    print("Generating SkyMarshal Architecture Diagrams...")
    print("-" * 50)

    print("1. Creating main architecture diagram...")
    create_architecture_diagram()
    print("   ✓ Created: skymarshal_architecture.png")

    print("2. Creating simplified overview diagram...")
    create_simplified_diagram()
    print("   ✓ Created: skymarshal_architecture_simple.png")

    print("3. Creating data flow diagram...")
    create_data_flow_diagram()
    print("   ✓ Created: skymarshal_dataflow.png")

    print("-" * 50)
    print("All diagrams generated successfully!")
    print(f"Output directory: {SCRIPT_DIR}")

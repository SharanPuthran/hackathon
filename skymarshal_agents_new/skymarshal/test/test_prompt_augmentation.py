"""Tests for prompt augmentation functions."""

import pytest
from main import augment_prompt_phase1, augment_prompt_phase2


def test_augment_prompt_phase1_preserves_original():
    """Test that phase 1 augmentation preserves original prompt."""
    original = "Flight EY123 on January 20th had a mechanical failure"
    augmented = augment_prompt_phase1(original)
    
    # Original prompt should be preserved at the start
    assert augmented.startswith(original)
    
    # Should contain phase 1 instruction
    assert "Please analyze this disruption and provide your initial recommendation" in augmented
    assert "from your domain perspective" in augmented


def test_augment_prompt_phase1_format():
    """Test that phase 1 augmentation has correct format."""
    original = "Test prompt"
    augmented = augment_prompt_phase1(original)
    
    # Should have original, newlines, then instruction
    expected_instruction = "Please analyze this disruption and provide your initial recommendation from your domain perspective."
    assert augmented == f"{original}\n\n{expected_instruction}"


def test_augment_prompt_phase2_preserves_original():
    """Test that phase 2 augmentation preserves original prompt."""
    original = "Flight EY123 on January 20th had a mechanical failure"
    collation = {
        "responses": {
            "crew_compliance": {
                "recommendation": "Crew is available",
                "confidence": 0.95,
                "binding_constraints": ["Must have 2 pilots"]
            },
            "maintenance": {
                "recommendation": "Aircraft needs inspection",
                "confidence": 0.85
            }
        }
    }
    
    augmented = augment_prompt_phase2(original, collation)
    
    # Original prompt should be preserved at the start
    assert augmented.startswith(original)
    
    # Should contain phase 2 instruction
    assert "Review other agents' recommendations and revise if needed" in augmented


def test_augment_prompt_phase2_includes_recommendations():
    """Test that phase 2 augmentation includes other agents' recommendations."""
    original = "Test prompt"
    collation = {
        "responses": {
            "crew_compliance": {
                "recommendation": "Crew is available",
                "confidence": 0.95,
                "binding_constraints": ["Must have 2 pilots"]
            },
            "maintenance": {
                "recommendation": "Aircraft needs inspection",
                "confidence": 0.85
            }
        }
    }
    
    augmented = augment_prompt_phase2(original, collation)
    
    # Should include agent names
    assert "CREW_COMPLIANCE" in augmented
    assert "MAINTENANCE" in augmented
    
    # Should include recommendations
    assert "Crew is available" in augmented
    assert "Aircraft needs inspection" in augmented
    
    # Should include confidence scores
    assert "0.95" in augmented
    assert "0.85" in augmented
    
    # Should include binding constraints
    assert "Must have 2 pilots" in augmented


def test_augment_prompt_phase2_empty_collation():
    """Test phase 2 augmentation with empty collation."""
    original = "Test prompt"
    collation = {"responses": {}}
    
    augmented = augment_prompt_phase2(original, collation)
    
    # Should still preserve original and include instruction
    assert augmented.startswith(original)
    assert "Review other agents' recommendations and revise if needed" in augmented


def test_augment_prompt_phase2_missing_fields():
    """Test phase 2 augmentation handles missing fields gracefully."""
    original = "Test prompt"
    collation = {
        "responses": {
            "crew_compliance": {
                # Missing recommendation, confidence, binding_constraints
            }
        }
    }
    
    augmented = augment_prompt_phase2(original, collation)
    
    # Should not crash and should include agent name
    assert "CREW_COMPLIANCE" in augmented
    assert "N/A" in augmented  # Default for missing fields


def test_prompt_augmentation_no_parsing():
    """Test that augmentation does not parse or extract from prompt."""
    # Use a prompt with various date formats and flight numbers
    original = "Flight EY123 on 20/01/2026 and flight AA456 yesterday both delayed"
    
    # Phase 1
    augmented1 = augment_prompt_phase1(original)
    assert original in augmented1  # Exact preservation
    
    # Phase 2
    collation = {"responses": {}}
    augmented2 = augment_prompt_phase2(original, collation)
    assert original in augmented2  # Exact preservation
    
    # No extraction or modification of the original content
    assert "EY123" in augmented1 and "EY123" in augmented2
    assert "20/01/2026" in augmented1 and "20/01/2026" in augmented2
    assert "AA456" in augmented1 and "AA456" in augmented2
    assert "yesterday" in augmented1 and "yesterday" in augmented2

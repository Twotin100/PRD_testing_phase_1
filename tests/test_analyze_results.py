"""Tests for the analyze_results module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.analyze_results import (
    ExtractionAnalyzer,
    analyze_failure_patterns,
    compare_to_ground_truth,
    create_ground_truth_template,
    generate_summary_report,
    make_go_nogo_recommendation,
)


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return [
        {
            "url": "https://example-kennels.co.uk",
            "business_type": "dog_kennel",
            "extraction_success": True,
            "quality_score": 75,
            "price_count": 3,
            "has_business_name": True,
            "has_contact_info": True,
            "extraction_time": 25.5,
            "source_file": "dog_kennel_example_metrics.json"
        },
        {
            "url": "https://happy-paws.co.uk",
            "business_type": "dog_groomer",
            "extraction_success": True,
            "quality_score": 60,
            "price_count": 5,
            "has_business_name": True,
            "has_contact_info": True,
            "extraction_time": 32.1,
            "source_file": "dog_groomer_happy_metrics.json"
        },
        {
            "url": "https://failed-site.co.uk",
            "business_type": "veterinary_clinic",
            "extraction_success": False,
            "quality_score": 20,
            "price_count": 0,
            "has_business_name": False,
            "has_contact_info": False,
            "extraction_time": 45.0,
            "error_message": "Timeout error: Site took too long to load",
            "source_file": "veterinary_failed_metrics.json"
        },
        {
            "url": "https://cat-hotel.co.uk",
            "business_type": "cattery",
            "extraction_success": True,
            "quality_score": 85,
            "price_count": 2,
            "has_business_name": True,
            "has_contact_info": True,
            "extraction_time": 18.3,
            "source_file": "cattery_cat_metrics.json"
        }
    ]


@pytest.fixture
def sample_extracted_data():
    """Sample extracted data for testing."""
    return [
        {
            "url": "https://example-kennels.co.uk",
            "business_name": "Example Kennels Ltd",
            "business_type": "dog_kennel",
            "contact": {
                "phone": "01234 567890",
                "email": "info@example-kennels.co.uk"
            },
            "services": [
                {"service_name": "Standard Kennel", "price": 25.0, "unit": "per_night"},
                {"service_name": "Deluxe Suite", "price": 35.0, "unit": "per_night"},
                {"service_name": "Second Dog", "price": 20.0, "unit": "per_night"}
            ],
            "source_file": "dog_kennel_example_extracted.json"
        },
        {
            "url": "https://happy-paws.co.uk",
            "business_name": "Happy Paws Grooming",
            "business_type": "dog_groomer",
            "contact": {
                "phone": "01234 567891",
                "email": "hello@happy-paws.co.uk"
            },
            "services": [
                {"service_name": "Small Dog Groom", "price": 30.0, "unit": "per_session"},
                {"service_name": "Large Dog Groom", "price": 45.0, "unit": "per_session"}
            ],
            "source_file": "dog_groomer_happy_extracted.json"
        }
    ]


@pytest.fixture
def sample_ground_truth():
    """Sample ground truth data for testing."""
    return {
        "_instructions": "Test ground truth data",
        "_created": "2025-01-15T10:00:00",
        "urls": [
            {
                "url": "https://example-kennels.co.uk",
                "business_type": "dog_kennel",
                "business_name": "Example Kennels Ltd",
                "phone": "01234 567890",
                "email": "info@example-kennels.co.uk",
                "address": "123 Farm Road, Somewhere, AB1 2CD",
                "services": [
                    {"service_name": "Standard Kennel", "price": 25.0, "unit": "per_night"},
                    {"service_name": "Deluxe Suite", "price": 35.0, "unit": "per_night"},
                    {"service_name": "Second Dog", "price": 20.0, "unit": "per_night"}
                ],
                "vaccination_requirements": ["Distemper", "Parvovirus"],
                "policies": {
                    "cancellation_policy": "24 hours notice required",
                    "deposit_policy": "50% deposit required"
                },
                "verification_notes": "All data verified manually"
            }
        ]
    }


@pytest.fixture
def temp_results_dir(sample_metrics_data, sample_extracted_data):
    """Create temporary results directory with sample data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create metrics files
        for i, metrics in enumerate(sample_metrics_data):
            metrics_file = temp_path / f"test_{i}_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f)
        
        # Create extracted data files
        for i, extracted in enumerate(sample_extracted_data):
            extracted_file = temp_path / f"test_{i}_extracted.json"
            with open(extracted_file, 'w') as f:
                json.dump(extracted, f)
        
        yield str(temp_path)


class TestExtractionAnalyzer:
    """Test the ExtractionAnalyzer class."""
    
    def test_init_loads_data(self, temp_results_dir):
        """Test that analyzer loads data correctly."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        assert len(analyzer.metrics_data) == 4
        assert len(analyzer.extracted_data) == 2
        assert analyzer.results_dir == Path(temp_results_dir)
    
    def test_init_nonexistent_directory(self):
        """Test initialization with non-existent directory."""
        with pytest.raises(FileNotFoundError):
            ExtractionAnalyzer("/nonexistent/directory")
    
    def test_generate_summary_report(self, temp_results_dir):
        """Test summary report generation."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        report = analyzer.generate_summary_report()
        
        assert "EXTRACTION TEST SUMMARY" in report
        assert "Total URLs tested: 4" in report
        assert "Successful extractions: 3 (75.0%)" in report
        assert "dog_kennel" in report
        assert "dog_groomer" in report
        assert "veterinary_clinic" in report
        assert "cattery" in report
    
    def test_generate_summary_report_empty_data(self):
        """Test summary report with no data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = ExtractionAnalyzer(temp_dir)
            report = analyzer.generate_summary_report()
            assert "No metrics data found" in report
    
    def test_create_ground_truth_template(self, temp_results_dir):
        """Test ground truth template creation."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        template = analyzer.create_ground_truth_template()
        
        assert "_instructions" in template
        assert "_created" in template
        assert "urls" in template
        assert len(template["urls"]) == 4
        
        # Check template structure
        url_template = template["urls"][0]
        assert "url" in url_template
        assert "business_type" in url_template
        assert "business_name" in url_template
        assert "services" in url_template
        assert "verification_notes" in url_template
    
    def test_compare_to_ground_truth(self, temp_results_dir, sample_ground_truth):
        """Test comparison to ground truth data."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        # Create temporary ground truth file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_ground_truth, f)
            gt_file = f.name
        
        try:
            results = analyzer.compare_to_ground_truth(gt_file)
            
            assert results["total_verified"] == 1
            assert results["name_accuracy"] == 1.0  # Perfect match
            assert results["price_accuracy"] == 1.0  # All prices match
            assert "detailed_results" in results
            assert len(results["detailed_results"]) == 1
        finally:
            os.unlink(gt_file)
    
    def test_compare_to_ground_truth_missing_file(self, temp_results_dir):
        """Test comparison with missing ground truth file."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        with pytest.raises(ValueError, match="Could not load ground truth file"):
            analyzer.compare_to_ground_truth("/nonexistent/file.json")
    
    def test_analyze_failure_patterns(self, temp_results_dir):
        """Test failure pattern analysis."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        patterns = analyzer.analyze_failure_patterns()
        
        assert patterns["total_failures"] == 1
        assert "error_categories" in patterns
        assert "timeout" in patterns["error_categories"]
        assert len(patterns["error_categories"]["timeout"]) == 1
        assert "recommendations" in patterns
    
    def test_make_go_nogo_recommendation_proceed(self, temp_results_dir):
        """Test go/no-go recommendation with good metrics."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        recommendation = analyzer.make_go_nogo_recommendation()
        
        assert recommendation["decision"] in ["PROCEED", "PROCEED_WITH_CAUTION", "REFINE"]
        assert "reasoning" in recommendation
        assert "metrics" in recommendation
        assert "next_steps" in recommendation
        
        metrics = recommendation["metrics"]
        assert metrics["total_urls"] == 4
        assert metrics["average_quality_score"] > 0
        assert metrics["pricing_found_percentage"] > 0
    
    def test_categorize_error(self, temp_results_dir):
        """Test error categorization."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        assert analyzer._categorize_error("Timeout error occurred") == "timeout"
        assert analyzer._categorize_error("JavaScript failed to load") == "javascript_issues"
        assert analyzer._categorize_error("PDF content not accessible") == "pdf_content"
        assert analyzer._categorize_error("Schema validation failed") == "schema_validation"
        assert analyzer._categorize_error("Network connection error") == "network_issues"
        assert analyzer._categorize_error("Rate limit exceeded") == "rate_limiting"
        assert analyzer._categorize_error("Unknown error") == "other"
    
    def test_apply_decision_matrix(self, temp_results_dir):
        """Test decision matrix application."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        # Test all decision matrix combinations
        assert analyzer._apply_decision_matrix(40, 50) == "STOP"
        assert analyzer._apply_decision_matrix(55, 50) == "REFINE"
        assert analyzer._apply_decision_matrix(70, 50) == "REFINE"
        
        assert analyzer._apply_decision_matrix(40, 70) == "REFINE"
        assert analyzer._apply_decision_matrix(55, 70) == "PROCEED_WITH_CAUTION"
        assert analyzer._apply_decision_matrix(70, 70) == "PROCEED"
        
        assert analyzer._apply_decision_matrix(40, 80) == "REFINE"
        assert analyzer._apply_decision_matrix(55, 80) == "PROCEED"
        assert analyzer._apply_decision_matrix(70, 80) == "PROCEED"
    
    def test_find_extracted_data(self, temp_results_dir):
        """Test finding extracted data by URL."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        data = analyzer._find_extracted_data("https://example-kennels.co.uk")
        assert data is not None
        assert data["business_name"] == "Example Kennels Ltd"
        
        data = analyzer._find_extracted_data("https://nonexistent.co.uk")
        assert data is None


class TestModuleFunctions:
    """Test module-level functions."""
    
    def test_generate_summary_report(self, temp_results_dir):
        """Test generate_summary_report function."""
        report = generate_summary_report(temp_results_dir)
        assert "EXTRACTION TEST SUMMARY" in report
        assert "Total URLs tested: 4" in report
    
    def test_create_ground_truth_template(self, temp_results_dir):
        """Test create_ground_truth_template function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_template.json")
            result_file = create_ground_truth_template(temp_results_dir, output_file)
            
            assert result_file == output_file
            assert os.path.exists(output_file)
            
            with open(output_file, 'r') as f:
                template = json.load(f)
            
            assert "_instructions" in template
            assert "urls" in template
            assert len(template["urls"]) == 4
    
    def test_create_ground_truth_template_default_output(self, temp_results_dir):
        """Test create_ground_truth_template with default output location."""
        result_file = create_ground_truth_template(temp_results_dir)
        expected_file = os.path.join(temp_results_dir, "ground_truth_template.json")
        
        assert result_file == expected_file
        assert os.path.exists(expected_file)
    
    def test_compare_to_ground_truth(self, temp_results_dir, sample_ground_truth):
        """Test compare_to_ground_truth function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_ground_truth, f)
            gt_file = f.name
        
        try:
            results = compare_to_ground_truth(temp_results_dir, gt_file)
            assert results["total_verified"] == 1
            assert "name_accuracy" in results
            assert "price_accuracy" in results
        finally:
            os.unlink(gt_file)
    
    def test_analyze_failure_patterns(self, temp_results_dir):
        """Test analyze_failure_patterns function."""
        patterns = analyze_failure_patterns(temp_results_dir)
        assert patterns["total_failures"] == 1
        assert "error_categories" in patterns
        assert "recommendations" in patterns
    
    def test_make_go_nogo_recommendation(self, temp_results_dir):
        """Test make_go_nogo_recommendation function."""
        recommendation = make_go_nogo_recommendation(temp_results_dir)
        assert "decision" in recommendation
        assert "reasoning" in recommendation
        assert "metrics" in recommendation
        assert "next_steps" in recommendation


class TestDecisionMatrix:
    """Test decision matrix logic with various scenarios."""
    
    @pytest.fixture
    def analyzer(self, temp_results_dir):
        """Create analyzer for testing."""
        return ExtractionAnalyzer(temp_results_dir)
    
    def test_stop_decision(self, analyzer):
        """Test STOP decision scenarios."""
        # Low quality, low pricing
        assert analyzer._apply_decision_matrix(30, 40) == "STOP"
        assert analyzer._apply_decision_matrix(45, 55) == "STOP"
    
    def test_refine_decision(self, analyzer):
        """Test REFINE decision scenarios."""
        # Various refine scenarios
        assert analyzer._apply_decision_matrix(55, 40) == "REFINE"  # Medium quality, low pricing
        assert analyzer._apply_decision_matrix(70, 40) == "REFINE"  # High quality, low pricing
        assert analyzer._apply_decision_matrix(30, 70) == "REFINE"  # Low quality, good pricing
    
    def test_proceed_with_caution_decision(self, analyzer):
        """Test PROCEED_WITH_CAUTION decision scenarios."""
        # Medium quality, medium pricing
        assert analyzer._apply_decision_matrix(55, 65) == "PROCEED_WITH_CAUTION"
        assert analyzer._apply_decision_matrix(60, 70) == "PROCEED_WITH_CAUTION"
    
    def test_proceed_decision(self, analyzer):
        """Test PROCEED decision scenarios."""
        # High quality scenarios
        assert analyzer._apply_decision_matrix(70, 65) == "PROCEED"
        assert analyzer._apply_decision_matrix(80, 80) == "PROCEED"
        
        # Medium quality, high pricing
        assert analyzer._apply_decision_matrix(55, 80) == "PROCEED"
    
    def test_next_steps_proceed(self, analyzer):
        """Test next steps for PROCEED decision."""
        steps = analyzer._get_next_steps("PROCEED", 70, 80)
        assert "Document successful approach" in steps
        assert "Scale to 100-URL validation batch" in steps
        assert "Begin production extraction" in steps
    
    def test_next_steps_refine(self, analyzer):
        """Test next steps for REFINE decision."""
        steps = analyzer._get_next_steps("REFINE", 45, 50)
        assert "Analyze failure patterns in detail" in steps
        assert "Consider alternative extraction approaches" in steps
        assert "Focus on improving overall extraction quality" in steps
        assert "Focus on improving pricing extraction accuracy" in steps
    
    def test_next_steps_stop(self, analyzer):
        """Test next steps for STOP decision."""
        steps = analyzer._get_next_steps("STOP", 30, 40)
        assert "Document limitations of automated extraction" in steps
        assert "Consider alternative approaches" in steps
        assert "Re-scope project based on findings" in steps


class TestMainCLI:
    """Test the main CLI interface."""
    
    @patch('sys.argv', ['analyze_results.py', 'test_dir', '--create-template'])
    @patch('src.analyze_results.create_ground_truth_template')
    def test_main_create_template(self, mock_create_template):
        """Test main function with create template option."""
        mock_create_template.return_value = "test_template.json"
        
        from src.analyze_results import main
        
        with patch('builtins.print') as mock_print:
            main()
            mock_create_template.assert_called_once_with('test_dir', None)
            mock_print.assert_called_with("Ground truth template created: test_template.json")
    
    @patch('sys.argv', ['analyze_results.py', 'test_dir'])
    @patch('src.analyze_results.generate_summary_report')
    @patch('src.analyze_results.analyze_failure_patterns')
    @patch('src.analyze_results.make_go_nogo_recommendation')
    def test_main_full_analysis(self, mock_recommendation, mock_patterns, mock_summary):
        """Test main function with full analysis."""
        mock_summary.return_value = "Test summary"
        mock_patterns.return_value = {
            'total_failures': 1,
            'error_categories': {'timeout': [{'business_type': 'test', 'error': 'test error'}]},
            'recommendations': ['Test recommendation']
        }
        mock_recommendation.return_value = {
            'decision': 'PROCEED',
            'reasoning': 'Test reasoning',
            'next_steps': ['Test step']
        }
        
        from src.analyze_results import main
        
        with patch('builtins.print'):
            main()
            
            mock_summary.assert_called_once_with('test_dir')
            mock_patterns.assert_called_once_with('test_dir')
            mock_recommendation.assert_called_once_with('test_dir')


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_metrics_data(self):
        """Test analyzer with empty metrics data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = ExtractionAnalyzer(temp_dir)
            
            # Should handle empty data gracefully
            report = analyzer.generate_summary_report()
            assert "No metrics data found" in report
            
            recommendation = analyzer.make_go_nogo_recommendation()
            assert recommendation["decision"] == "INSUFFICIENT_DATA"
    
    def test_malformed_json_files(self):
        """Test handling of malformed JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create malformed JSON file
            bad_file = temp_path / "bad_metrics.json"
            with open(bad_file, 'w') as f:
                f.write("{ invalid json }")
            
            # Should handle gracefully with warning
            with patch('builtins.print') as mock_print:
                analyzer = ExtractionAnalyzer(temp_dir)
                assert len(analyzer.metrics_data) == 0
                mock_print.assert_called()
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields in data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create metrics file with missing fields
            metrics_file = temp_path / "incomplete_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump({"url": "test.com"}, f)  # Missing most fields
            
            analyzer = ExtractionAnalyzer(temp_dir)
            
            # Should handle missing fields gracefully
            report = analyzer.generate_summary_report()
            assert "Total URLs tested: 1" in report
            
            recommendation = analyzer.make_go_nogo_recommendation()
            assert "decision" in recommendation
    
    def test_ground_truth_comparison_no_matches(self, temp_results_dir):
        """Test ground truth comparison with no matching URLs."""
        analyzer = ExtractionAnalyzer(temp_results_dir)
        
        # Ground truth with different URLs
        ground_truth = {
            "urls": [
                {
                    "url": "https://different-site.co.uk",
                    "business_name": "Different Business",
                    "services": []
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(ground_truth, f)
            gt_file = f.name
        
        try:
            results = analyzer.compare_to_ground_truth(gt_file)
            assert results["total_verified"] == 0
            assert results["name_accuracy"] == 0.0
        finally:
            os.unlink(gt_file)
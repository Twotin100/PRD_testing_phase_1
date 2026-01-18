#!/usr/bin/env python3
"""
Analysis and reporting tools for extraction results.

This module provides tools for analyzing extraction results and generating reports
for go/no-go decisions as specified in the PRD sections 9 and 11.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def _safe_col(df: pd.DataFrame, col: str, default: Any = None) -> pd.Series:
    """Safely get a DataFrame column with a default value if column doesn't exist."""
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def _safe_col_scalar(df: pd.DataFrame, col: str, default: Any) -> pd.Series:
    """Get column or return Series filled with scalar default for comparisons."""
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


class ExtractionAnalyzer:
    """Analyzer for extraction results and reporting."""
    
    def __init__(self, results_dir: str):
        """Initialize analyzer with results directory."""
        self.results_dir = Path(results_dir)
        self.metrics_data: List[Dict[str, Any]] = []
        self.extracted_data: List[Dict[str, Any]] = []
        self._load_results()
    
    def _load_results(self) -> None:
        """Load all metrics and extracted data from results directory."""
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {self.results_dir}")
        
        # Load metrics files
        for metrics_file in self.results_dir.glob("*_metrics.json"):
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    metrics = json.load(f)
                    metrics['source_file'] = metrics_file.name
                    self.metrics_data.append(metrics)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {metrics_file}: {e}")
        
        # Load extracted data files
        for extracted_file in self.results_dir.glob("*_extracted.json"):
            try:
                with open(extracted_file, 'r', encoding='utf-8') as f:
                    extracted = json.load(f)
                    extracted['source_file'] = extracted_file.name
                    self.extracted_data.append(extracted)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {extracted_file}: {e}")
    
    def generate_summary_report(self) -> str:
        """Generate comprehensive summary report of extraction results."""
        if not self.metrics_data:
            return "No metrics data found to analyze."
        
        df = pd.DataFrame(self.metrics_data)
        
        # Overall metrics
        total_urls = len(df)
        successful_extractions = len(df[_safe_col_scalar(df, 'extraction_success', False) == True])
        success_rate = (successful_extractions / total_urls * 100) if total_urls > 0 else 0
        avg_quality_score = _safe_col(df, 'quality_score', 0).mean()
        urls_with_pricing = len(df[_safe_col_scalar(df, 'price_count', 0) > 0])
        pricing_rate = (urls_with_pricing / total_urls * 100) if total_urls > 0 else 0
        
        report = []
        report.append("EXTRACTION TEST SUMMARY")
        report.append("=" * 50)
        report.append("")
        report.append("Overall Metrics:")
        report.append(f"  Total URLs tested: {total_urls}")
        report.append(f"  Successful extractions: {successful_extractions} ({success_rate:.1f}%)")
        report.append(f"  Average quality score: {avg_quality_score:.1f}")
        report.append(f"  URLs with pricing found: {urls_with_pricing} ({pricing_rate:.1f}%)")
        report.append("")
        
        # Per-business-type breakdown
        if 'business_type' in df.columns:
            report.append("By Business Type:")
            type_stats = []
            
            for business_type in df['business_type'].unique():
                if pd.isna(business_type):
                    continue
                    
                type_df = df[df['business_type'] == business_type]
                type_total = len(type_df)
                type_success = len(type_df[_safe_col_scalar(type_df, 'extraction_success', False) == True])
                type_success_rate = (type_success / type_total * 100) if type_total > 0 else 0
                type_avg_score = _safe_col(type_df, 'quality_score', 0).mean()
                type_pricing = len(type_df[_safe_col_scalar(type_df, 'price_count', 0) > 0])
                type_pricing_rate = (type_pricing / type_total * 100) if type_total > 0 else 0
                
                type_stats.append({
                    'Type': business_type,
                    'Tested': type_total,
                    'Success': f"{type_success}/{type_total}",
                    'Success Rate': f"{type_success_rate:.1f}%",
                    'Avg Score': f"{type_avg_score:.1f}",
                    'Has Prices': f"{type_pricing_rate:.0f}%"
                })
            
            # Format as table
            if type_stats:
                report.append("  ┌──────────────────┬────────┬─────────┬─────────────┬───────────┬────────────┐")
                report.append("  │ Type             │ Tested │ Success │ Success Rate│ Avg Score │ Has Prices │")
                report.append("  ├──────────────────┼────────┼─────────┼─────────────┼───────────┼────────────┤")
                
                for stat in type_stats:
                    report.append(f"  │ {stat['Type']:<16} │ {stat['Tested']:>6} │ {stat['Success']:>7} │ {stat['Success Rate']:>11} │ {stat['Avg Score']:>9} │ {stat['Has Prices']:>10} │")
                
                report.append("  └──────────────────┴────────┴─────────┴─────────────┴───────────┴────────────┘")
        
        report.append("")
        
        # Performance metrics
        if 'extraction_time' in df.columns:
            avg_time = df['extraction_time'].mean()
            max_time = df['extraction_time'].max()
            report.append("Performance Metrics:")
            report.append(f"  Average extraction time: {avg_time:.1f}s")
            report.append(f"  Maximum extraction time: {max_time:.1f}s")
            report.append("")
        
        # Quality distribution
        if 'quality_score' in df.columns:
            high_quality = len(df[df['quality_score'] >= 65])
            medium_quality = len(df[(df['quality_score'] >= 50) & (df['quality_score'] < 65)])
            low_quality = len(df[df['quality_score'] < 50])
            
            report.append("Quality Score Distribution:")
            report.append(f"  High quality (≥65): {high_quality} ({high_quality/total_urls*100:.1f}%)")
            report.append(f"  Medium quality (50-64): {medium_quality} ({medium_quality/total_urls*100:.1f}%)")
            report.append(f"  Low quality (<50): {low_quality} ({low_quality/total_urls*100:.1f}%)")
            report.append("")
        
        # Common errors
        if 'error_message' in df.columns:
            error_mask = df['error_message'].notna() & (df['error_message'] != '')
            errors = df[error_mask]
        else:
            errors = pd.DataFrame()
        if not errors.empty:
            report.append("Common Errors:")
            error_counts = errors['error_message'].value_counts().head(5)
            for error, count in error_counts.items():
                report.append(f"  • {error}: {count} occurrences")
            report.append("")
        
        return "\n".join(report)
    
    def create_ground_truth_template(self) -> Dict[str, Any]:
        """Create template for manual verification ground truth data."""
        template = {
            "_instructions": "Fill in expected values by checking actual websites",
            "_created": datetime.now().isoformat(),
            "urls": []
        }
        
        for metrics in self.metrics_data:
            url_template = {
                "url": metrics.get('url', ''),
                "business_type": metrics.get('business_type', ''),
                "business_name": "",
                "phone": "",
                "email": "",
                "address": "",
                "services": [
                    {
                        "service_name": "",
                        "price": 0.00,
                        "unit": ""
                    }
                ],
                "vaccination_requirements": [],
                "policies": {
                    "cancellation_policy": "",
                    "deposit_policy": ""
                },
                "verification_notes": "",
                "_source_file": metrics.get('source_file', ''),
                "_quality_score": metrics.get('quality_score', 0)
            }
            template["urls"].append(url_template)
        
        return template
    
    def compare_to_ground_truth(self, ground_truth_file: str) -> Dict[str, Any]:
        """Compare extracted results to manually verified ground truth."""
        try:
            with open(ground_truth_file, 'r', encoding='utf-8') as f:
                ground_truth = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not load ground truth file: {e}")
        
        results = {
            "total_verified": 0,
            "name_accuracy": 0.0,
            "price_accuracy": 0.0,
            "field_coverage": 0.0,
            "overall_accuracy": 0.0,
            "detailed_results": []
        }
        
        verified_urls = ground_truth.get("urls", [])
        total_verified = len([url for url in verified_urls if url.get("business_name")])
        
        if total_verified == 0:
            return results
        
        name_matches = 0
        total_expected_prices = 0
        correct_prices = 0
        total_fields_expected = 0
        total_fields_found = 0
        
        for gt_url in verified_urls:
            if not gt_url.get("business_name"):  # Skip unverified entries
                continue
            
            # Find corresponding extracted data
            extracted = self._find_extracted_data(gt_url["url"])
            if not extracted:
                continue
            
            url_result = {
                "url": gt_url["url"],
                "name_match": False,
                "price_accuracy": 0.0,
                "field_coverage": 0.0,
                "issues": []
            }
            
            # Check business name accuracy
            extracted_name = extracted.get("business_name", "").lower().strip()
            expected_name = gt_url.get("business_name", "").lower().strip()
            
            if extracted_name and expected_name:
                # Simple similarity check - exact match or one contains the other
                name_match = (extracted_name == expected_name or 
                             extracted_name in expected_name or 
                             expected_name in extracted_name)
                if name_match:
                    name_matches += 1
                    url_result["name_match"] = True
                else:
                    url_result["issues"].append(f"Name mismatch: '{extracted_name}' vs '{expected_name}'")
            
            # Check price accuracy
            expected_services = gt_url.get("services", [])
            extracted_services = extracted.get("services", [])
            
            if expected_services:
                expected_prices = [s.get("price", 0) for s in expected_services if s.get("price")]
                total_expected_prices += len(expected_prices)
                
                for exp_service in expected_services:
                    exp_price = exp_service.get("price", 0)
                    if exp_price <= 0:
                        continue
                    
                    # Find matching service in extracted data
                    found_match = False
                    for ext_service in extracted_services:
                        ext_price = ext_service.get("price", 0)
                        if ext_price > 0:
                            # Consider match if within 10% or exact
                            if abs(ext_price - exp_price) / exp_price <= 0.1:
                                correct_prices += 1
                                found_match = True
                                break
                    
                    if not found_match:
                        url_result["issues"].append(f"Missing price: {exp_service.get('service_name', 'Unknown')} - £{exp_price}")
            
            # Check field coverage
            expected_fields = ["business_name", "phone", "email", "address"]
            found_fields = 0
            
            for field in expected_fields:
                total_fields_expected += 1
                if gt_url.get(field) and extracted.get(field):
                    found_fields += 1
                    total_fields_found += 1
                elif gt_url.get(field) and not extracted.get(field):
                    url_result["issues"].append(f"Missing field: {field}")
            
            url_result["field_coverage"] = found_fields / len(expected_fields) if expected_fields else 0
            url_result["price_accuracy"] = (correct_prices / len(expected_prices)) if expected_prices else 0
            
            results["detailed_results"].append(url_result)
        
        # Calculate overall metrics
        results["total_verified"] = total_verified
        results["name_accuracy"] = name_matches / total_verified if total_verified > 0 else 0
        results["price_accuracy"] = correct_prices / total_expected_prices if total_expected_prices > 0 else 0
        results["field_coverage"] = total_fields_found / total_fields_expected if total_fields_expected > 0 else 0
        results["overall_accuracy"] = (results["name_accuracy"] + results["price_accuracy"] + results["field_coverage"]) / 3
        
        return results
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze common failure patterns and categorize errors."""
        patterns = {
            "total_failures": 0,
            "error_categories": {},
            "quality_issues": {},
            "recommendations": []
        }
        
        df = pd.DataFrame(self.metrics_data)

        # Count failures
        failures = df[_safe_col_scalar(df, 'extraction_success', True) == False]
        patterns["total_failures"] = len(failures)
        
        # Categorize errors
        error_categories = {}
        for _, row in failures.iterrows():
            error_msg = row.get('error_message', 'Unknown error')
            
            # Categorize common error types
            category = self._categorize_error(error_msg)
            if category not in error_categories:
                error_categories[category] = []
            error_categories[category].append({
                'url': row.get('url', ''),
                'business_type': row.get('business_type', ''),
                'error': error_msg
            })
        
        patterns["error_categories"] = error_categories

        # Analyze quality issues
        quality_scores = _safe_col_scalar(df, 'quality_score', 100)
        low_quality = df[quality_scores < 50]
        medium_quality = df[(quality_scores >= 50) & (quality_scores < 65)]

        quality_issues = {
            "low_quality_count": len(low_quality),
            "medium_quality_count": len(medium_quality),
            "common_issues": []
        }

        # Identify common quality issues
        no_pricing = df[_safe_col_scalar(df, 'price_count', 0) == 0]
        no_contact = df[_safe_col_scalar(df, 'has_contact_info', True) == False]
        no_business_name = df[_safe_col_scalar(df, 'has_business_name', True) == False]
        
        if len(no_pricing) > 0:
            quality_issues["common_issues"].append(f"No pricing found: {len(no_pricing)} URLs")
        if len(no_contact) > 0:
            quality_issues["common_issues"].append(f"No contact info: {len(no_contact)} URLs")
        if len(no_business_name) > 0:
            quality_issues["common_issues"].append(f"No business name: {len(no_business_name)} URLs")
        
        patterns["quality_issues"] = quality_issues
        
        # Generate recommendations
        recommendations = []
        
        if "timeout" in str(error_categories):
            recommendations.append("Increase extraction timeout for complex sites")
        
        if "javascript" in str(error_categories).lower():
            recommendations.append("Increase waitFor timeout for JavaScript-heavy sites")
        
        if len(no_pricing) > len(df) * 0.3:  # More than 30% missing pricing
            recommendations.append("Review pricing extraction prompts and schemas")
        
        if patterns["total_failures"] > len(df) * 0.2:  # More than 20% failures
            recommendations.append("Consider fallback extraction strategies")
        
        # Business type specific recommendations
        if 'business_type' in df.columns:
            for business_type in df['business_type'].unique():
                if pd.isna(business_type):
                    continue
                type_df = df[df['business_type'] == business_type]
                type_avg_quality = _safe_col(type_df, 'quality_score', 100).mean()

                if type_avg_quality < 50:
                    recommendations.append(f"Refine {business_type} schema and extraction prompts")
        
        patterns["recommendations"] = recommendations
        
        return patterns
    
    def make_go_nogo_recommendation(self) -> Dict[str, Any]:
        """Make go/no-go recommendation based on decision matrix from PRD."""
        if not self.metrics_data:
            return {
                "decision": "INSUFFICIENT_DATA",
                "reasoning": "No metrics data available for analysis",
                "metrics": {}
            }
        
        df = pd.DataFrame(self.metrics_data)

        # Calculate key metrics
        total_urls = len(df)
        avg_quality_score = _safe_col(df, 'quality_score', 0).mean()
        urls_with_pricing = len(df[_safe_col_scalar(df, 'price_count', 0) > 0])
        pricing_percentage = (urls_with_pricing / total_urls * 100) if total_urls > 0 else 0
        
        metrics = {
            "total_urls": total_urls,
            "average_quality_score": avg_quality_score,
            "pricing_found_percentage": pricing_percentage,
            "urls_with_pricing": urls_with_pricing
        }
        
        # Apply decision matrix from PRD Section 11.1
        decision = self._apply_decision_matrix(avg_quality_score, pricing_percentage)
        
        # Generate reasoning
        reasoning_parts = [
            f"Average quality score: {avg_quality_score:.1f}",
            f"Pricing found in {pricing_percentage:.1f}% of URLs ({urls_with_pricing}/{total_urls})"
        ]
        
        # Add business type analysis
        if 'business_type' in df.columns:
            type_analysis = []
            for business_type in df['business_type'].unique():
                if pd.isna(business_type):
                    continue
                type_df = df[df['business_type'] == business_type]
                type_avg_quality = _safe_col(type_df, 'quality_score', 0).mean()
                type_pricing_rate = len(type_df[_safe_col_scalar(type_df, 'price_count', 0) > 0]) / len(type_df) * 100
                
                type_decision = self._apply_decision_matrix(type_avg_quality, type_pricing_rate)
                type_analysis.append(f"{business_type}: {type_decision} (Q:{type_avg_quality:.1f}, P:{type_pricing_rate:.1f}%)")
            
            if type_analysis:
                reasoning_parts.append("Per-type analysis: " + "; ".join(type_analysis))
        
        recommendation = {
            "decision": decision,
            "reasoning": "; ".join(reasoning_parts),
            "metrics": metrics,
            "next_steps": self._get_next_steps(decision, avg_quality_score, pricing_percentage)
        }
        
        return recommendation
    
    def _find_extracted_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Find extracted data for a given URL."""
        for extracted in self.extracted_data:
            if extracted.get('url') == url:
                return extracted
        return None
    
    def _categorize_error(self, error_msg: str) -> str:
        """Categorize error message into common types."""
        error_lower = error_msg.lower()
        
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'javascript' in error_lower or 'js' in error_lower:
            return 'javascript_issues'
        elif 'pdf' in error_lower:
            return 'pdf_content'
        elif 'schema' in error_lower or 'validation' in error_lower:
            return 'schema_validation'
        elif 'network' in error_lower or 'connection' in error_lower:
            return 'network_issues'
        elif 'rate limit' in error_lower:
            return 'rate_limiting'
        else:
            return 'other'
    
    def _apply_decision_matrix(self, quality_score: float, pricing_percentage: float) -> str:
        """Apply decision matrix from PRD Section 11.1."""
        # Decision matrix:
        # Quality Score:  <50   | 50-65  | >65
        # Pricing <60%:   STOP  | REFINE | REFINE
        # Pricing 60-75%: REFINE| PROCEED*| PROCEED
        # Pricing >75%:   REFINE| PROCEED | PROCEED
        
        if quality_score < 50:
            if pricing_percentage < 60:
                return "STOP"
            else:
                return "REFINE"
        elif quality_score < 65:
            if pricing_percentage < 60:
                return "REFINE"
            elif pricing_percentage < 75:
                return "PROCEED_WITH_CAUTION"
            else:
                return "PROCEED"
        else:  # quality_score >= 65
            if pricing_percentage < 60:
                return "REFINE"
            else:
                return "PROCEED"
    
    def _get_next_steps(self, decision: str, quality_score: float, pricing_percentage: float) -> List[str]:
        """Get recommended next steps based on decision."""
        steps = []
        
        if decision == "PROCEED":
            steps.extend([
                "Document successful approach",
                "Scale to 100-URL validation batch",
                "Build full infrastructure (database, storage)",
                "Begin production extraction"
            ])
        elif decision == "PROCEED_WITH_CAUTION":
            steps.extend([
                "Identify weakest business types",
                "Refine schemas/prompts for problem areas",
                "Run additional 20-URL test on refined approach",
                "Monitor closely during scale-up"
            ])
        elif decision == "REFINE":
            steps.extend([
                "Analyze failure patterns in detail",
                "Consider alternative extraction approaches",
                "Refine schemas and prompts",
                "Run refined test with 20 new URLs"
            ])
            
            if quality_score < 50:
                steps.append("Focus on improving overall extraction quality")
            if pricing_percentage < 60:
                steps.append("Focus on improving pricing extraction accuracy")
        elif decision == "STOP":
            steps.extend([
                "Document limitations of automated extraction",
                "Consider alternative approaches (manual, hybrid)",
                "Re-scope project based on findings",
                "Evaluate different extraction services"
            ])
        
        return steps


def generate_summary_report(results_dir: str) -> str:
    """Generate summary report for extraction results."""
    analyzer = ExtractionAnalyzer(results_dir)
    return analyzer.generate_summary_report()


def create_ground_truth_template(results_dir: str, output_file: Optional[str] = None) -> str:
    """Create ground truth template for manual verification."""
    analyzer = ExtractionAnalyzer(results_dir)
    template = analyzer.create_ground_truth_template()
    
    if output_file is None:
        output_file = os.path.join(results_dir, "ground_truth_template.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    return output_file


def compare_to_ground_truth(results_dir: str, ground_truth_file: str) -> Dict[str, Any]:
    """Compare extraction results to ground truth data."""
    analyzer = ExtractionAnalyzer(results_dir)
    return analyzer.compare_to_ground_truth(ground_truth_file)


def analyze_failure_patterns(results_dir: str) -> Dict[str, Any]:
    """Analyze failure patterns in extraction results."""
    analyzer = ExtractionAnalyzer(results_dir)
    return analyzer.analyze_failure_patterns()


def make_go_nogo_recommendation(results_dir: str) -> Dict[str, Any]:
    """Make go/no-go recommendation based on extraction results."""
    analyzer = ExtractionAnalyzer(results_dir)
    return analyzer.make_go_nogo_recommendation()


def main():
    """Main CLI interface for analysis tools."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze extraction results and generate reports")
    parser.add_argument("results_dir", help="Directory containing extraction results")
    parser.add_argument("--create-template", action="store_true", 
                       help="Create ground truth template")
    parser.add_argument("--ground-truth", help="Ground truth file for accuracy analysis")
    parser.add_argument("--output", help="Output file for reports")
    
    args = parser.parse_args()
    
    try:
        if args.create_template:
            output_file = create_ground_truth_template(args.results_dir, args.output)
            print(f"Ground truth template created: {output_file}")
            return
        
        # Generate comprehensive analysis
        print("EXTRACTION ANALYSIS REPORT")
        print("=" * 50)
        print()
        
        # Summary report
        summary = generate_summary_report(args.results_dir)
        print(summary)
        print()
        
        # Failure pattern analysis
        print("FAILURE PATTERN ANALYSIS")
        print("=" * 50)
        failure_analysis = analyze_failure_patterns(args.results_dir)
        
        print(f"Total failures: {failure_analysis['total_failures']}")
        print()
        
        if failure_analysis['error_categories']:
            print("Error Categories:")
            for category, errors in failure_analysis['error_categories'].items():
                print(f"  {category}: {len(errors)} occurrences")
                for error in errors[:3]:  # Show first 3 examples
                    print(f"    - {error['business_type']}: {error['error'][:100]}...")
            print()
        
        if failure_analysis['recommendations']:
            print("Recommendations:")
            for rec in failure_analysis['recommendations']:
                print(f"  • {rec}")
            print()
        
        # Go/No-Go recommendation
        print("GO/NO-GO RECOMMENDATION")
        print("=" * 50)
        recommendation = make_go_nogo_recommendation(args.results_dir)
        
        print(f"Decision: {recommendation['decision']}")
        print(f"Reasoning: {recommendation['reasoning']}")
        print()
        
        if recommendation.get('next_steps'):
            print("Next Steps:")
            for step in recommendation['next_steps']:
                print(f"  • {step}")
            print()
        
        # Accuracy analysis if ground truth provided
        if args.ground_truth:
            print("ACCURACY ANALYSIS")
            print("=" * 50)
            try:
                accuracy = compare_to_ground_truth(args.results_dir, args.ground_truth)
                print(f"Manual verification results ({accuracy['total_verified']} URLs):")
                print(f"  Name extraction accuracy: {accuracy['name_accuracy']:.1%}")
                print(f"  Price extraction accuracy: {accuracy['price_accuracy']:.1%}")
                print(f"  Field coverage: {accuracy['field_coverage']:.1%}")
                print(f"  Overall accuracy: {accuracy['overall_accuracy']:.1%}")
            except Exception as e:
                print(f"Could not perform accuracy analysis: {e}")
        
        # Save report if output specified
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(summary)
                f.write("\n\n")
                f.write(json.dumps(failure_analysis, indent=2))
                f.write("\n\n")
                f.write(json.dumps(recommendation, indent=2))
            print(f"Full report saved to: {args.output}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
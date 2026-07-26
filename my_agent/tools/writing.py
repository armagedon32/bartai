from my_agent.tools.registry import Tool


class WriteDocumentTool(Tool):
    name = "write_document"
    description = "Write professional documents: reports, articles, essays, emails, proposals, memos, presentations, technical docs, creative writing, and more across any field. Generates well-structured, publication-ready content. Use this for any professional writing task."
    parameters = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic or subject of the document.",
            },
            "document_type": {
                "type": "string",
                "enum": [
                    "report", "article", "essay", "email", "proposal",
                    "memo", "technical_doc", "presentation_outline",
                    "research_paper", "business_plan", "case_study",
                    "review", "tutorial", "creative_writing", "press_release",
                ],
                "description": "Type of document to write.",
            },
            "audience": {
                "type": "string",
                "description": "Target audience (e.g. 'general public', 'executives', 'technical team', 'academic', 'students').",
            },
            "tone": {
                "type": "string",
                "enum": ["professional", "academic", "casual", "persuasive", "technical", "creative"],
                "description": "Writing tone and style.",
            },
            "key_points": {
                "type": "string",
                "description": "Key points or sections to include, comma-separated.",
            },
            "word_count": {
                "type": "integer",
                "description": "Approximate target word count.",
            },
        },
        "required": ["topic", "document_type", "audience"],
    }

    def execute(self, topic: str, document_type: str, audience: str,
                tone: str = "professional", key_points: str = "", word_count: int = 0) -> str:
        points_list = [p.strip() for p in key_points.split(",") if p.strip()]
        points_str = ", ".join(points_list) if points_list else "Not specified"
        wc_hint = f" (target: ~{word_count} words)" if word_count > 0 else ""

        structures = {
            "report": "# {title}\n\n## Executive Summary\n\n## Introduction\n\n## Methodology\n\n## Findings\n\n## Analysis\n\n## Conclusion\n\n## Recommendations\n\n## References",
            "article": "# {title}\n\n## Introduction\n\n## Background\n\n## Main Body\n\n## Analysis\n\n## Conclusion\n\n---\n*Published by BArt AI*",
            "essay": "# {title}\n\n## Introduction\n\n## Thesis Statement\n\n## Body Paragraph 1\n\n## Body Paragraph 2\n\n## Body Paragraph 3\n\n## Counterarguments\n\n## Conclusion\n\n## References",
            "email": "**Subject:** {title}\n\nDear [Recipient],\n\n[Body]\n\nBest regards,\nBArt AI",
            "proposal": "# {title}\n\n## Executive Summary\n\n## Problem Statement\n\n## Proposed Solution\n\n## Implementation Plan\n\n## Timeline\n\n## Budget\n\n## Expected Outcomes\n\n## About Us",
            "memo": "**MEMORANDUM**\n\n**To:** [Recipients]\n**From:** BArt AI\n**Date:** [Date]\n**Subject:** {title}\n\n## Purpose\n\n## Background\n\n## Discussion\n\n## Action Items\n\n## Next Steps",
            "technical_doc": "# {title}\n\n## Overview\n\n## Prerequisites\n\n## Architecture\n\n## Installation / Setup\n\n## Configuration\n\n## Usage\n\n## API Reference\n\n## Troubleshooting\n\n##FAQ",
            "presentation_outline": "# {title}\n\n## Slide 1: Title Slide\n\n## Slide 2: Agenda\n\n## Slide 3: Introduction\n\n## Slide 4-7: Main Content\n\n## Slide 8: Case Study / Example\n\n## Slide 9: Key Takeaways\n\n## Slide 10: Q&A",
            "research_paper": "# {title}\n\n## Abstract\n\n## Introduction\n\n## Literature Review\n\n## Methodology\n\n## Results\n\n## Discussion\n\n## Conclusion\n\n## References",
            "business_plan": "# {title}\n\n## Executive Summary\n\n## Company Description\n\n## Market Analysis\n\n## Organization & Management\n\n## Products & Services\n\n## Marketing Strategy\n\n## Financial Projections\n\n## Funding Request\n\n## Appendix",
            "case_study": "# {title}\n\n## Background\n\n## Challenge\n\n## Approach\n\n## Solution\n\n## Results\n\n## Key Takeaways",
            "review": "# {title}\n\n## Overview\n\n## The Good\n\n## The Bad\n\n## Verdict\n\n## Rating",
            "tutorial": "# {title}\n\n## Introduction\n\n## Prerequisites\n\n## Step 1\n\n## Step 2\n\n## Step 3\n\n## Summary\n\n## Next Steps",
            "creative_writing": "# {title}\n\n[Creative work]\n\n---\n*Written by BArt AI*",
            "press_release": "**FOR IMMEDIATE RELEASE**\n\n# {title}\n\n[CITY, Date] — [Lead paragraph]\n\n## About\n\n## Contact\n\n###",
        }

        structure = structures.get(document_type, "# {title}\n\n[Content]")
        structure = structure.replace("{title}", topic)

        return (
            f"**Document Brief:**\n"
            f"- **Type:** {document_type.replace('_', ' ').title()}\n"
            f"- **Topic:** {topic}\n"
            f"- **Audience:** {audience}\n"
            f"- **Tone:** {tone}\n"
            f"- **Key Points:** {points_str}{wc_hint}\n\n"
            f"**Suggested Structure:**\n```\n{structure}\n```\n\n"
            f"[The AI will write the full document in its response based on this brief and the conversation context.]"
        )


class TranslateTool(Tool):
    name = "translate"
    description = "Translate text between any two languages. Supports all major world languages. Preserves formatting, tone, and context. Use for translating phrases, paragraphs, or entire documents."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to translate.",
            },
            "source_language": {
                "type": "string",
                "description": "Source language (e.g. 'English', 'Spanish', 'French', 'German', 'Chinese', 'Japanese', 'Arabic', 'Hindi', 'Russian', 'Portuguese'). Use 'auto' for automatic detection.",
            },
            "target_language": {
                "type": "string",
                "description": "Target language to translate into.",
            },
        },
        "required": ["text", "target_language"],
    }

    def execute(self, text: str, target_language: str, source_language: str = "auto") -> str:
        if not text.strip():
            return "No text provided to translate."
        src = f" from {source_language}" if source_language != "auto" else " (auto-detected)"
        return (
            f"**Translation Request:**{src} to {target_language}\n\n"
            f"**Original text:**\n{text}\n\n"
            f"**[The AI will provide the translation in its response based on this request.]**"
        )
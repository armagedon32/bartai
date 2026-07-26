import re
from my_agent.tools.registry import Tool


class CheckWritingTool(Tool):
    name = "check_writing"
    description = "Check text for grammar, spelling, punctuation, style issues, and readability. Returns specific issues found with suggestions for improvement. Use for proofreading essays, emails, reports, articles, or any written content."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to check for grammar, spelling, and style issues.",
            },
            "check_type": {
                "type": "string",
                "enum": ["grammar", "spelling", "style", "readability", "all"],
                "description": "What to check: grammar, spelling, style, readability, or all.",
            },
        },
        "required": ["text"],
    }

    def execute(self, text: str, check_type: str = "all") -> str:
        if not text.strip():
            return "No text provided to check."

        word_count = len(text.split())
        char_count = len(text)
        sentence_count = len(re.findall(r'[.!?]+', text)) or 1

        parts = [f"**Writing Check Report**\n"]
        parts.append(f"**Stats:** {word_count} words, {char_count} chars, {sentence_count} sentences\n")

        if check_type in ("readability", "all"):
            avg_words = word_count / sentence_count
            parts.append(f"**Readability:**\n")
            parts.append(f"- Avg sentence length: {avg_words:.1f} words ({'Good' if 15 <= avg_words <= 25 else 'Long' if avg_words > 25 else 'Short'})\n")

            long_sentences = 0
            for s in re.split(r'[.!?]+', text):
                if len(s.split()) > 30:
                    long_sentences += 1
            if long_sentences:
                parts.append(f"- {long_sentences} sentence(s) over 30 words — consider splitting\n")

            passive = len(re.findall(r'\b(is|are|was|were|be|been|being)\s+\w+ed\b', text, re.IGNORECASE))
            if passive > 0:
                parts.append(f"- {passive} possible passive voice usage(s)\n")

        if check_type in ("spelling", "all"):
            common_misspellings = {
                "recieve": "receive", "wierd": "weird", "occured": "occurred",
                "ocurred": "occurred", "accomodate": "accommodate", "acomodate": "accommodate",
                "embarass": "embarrass", "seperate": "separate", "definately": "definitely",
                "definately": "definitely", "goverment": "government", "goverment": "government",
                "alot": "a lot", "untill": "until", "writen": "written", "writting": "writing",
                "occassion": "occasion", "occassionally": "occasionally", "aquire": "acquire",
                "calender": "calendar", "concious": "conscious", "decaffinated": "decaffeinated",
                "eigth": "eighth", "enviroment": "environment", "esential": "essential",
                "extention": "extension", "febuary": "February", "fourty": "forty",
                "heros": "heroes", "immediatly": "immediately", "independant": "independent",
                "libary": "library", "miniture": "miniature", "neccessary": "necessary",
                "nineth": "ninth", "ninty": "ninety", "nintey": "ninety", "practise": "practice",
                "priviledge": "privilege", "privelege": "privilege", "reciept": "receipt",
                "reccomend": "recommend", "recomend": "recommend", "refered": "referred",
                "refering": "referring", "sence": "sense", "sargent": "sergeant",
                "sucess": "success", "succes": "success", "thier": "their", "tommorow": "tomorrow",
                "tommorrow": "tomorrow", "truely": "truly", "twelth": "twelfth",
                "wierd": "weird", "wierd": "weird", "beleive": "believe", "belive": "believe",
            }
            words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            found = {}
            for w in words:
                if w in common_misspellings:
                    found[w] = common_misspellings[w]
            if found:
                parts.append(f"\n**Possible Spelling Issues:**\n")
                for wrong, correct in found.items():
                    parts.append(f"- '{wrong}' -> '{correct}'\n")
            else:
                parts.append(f"\n**Spelling:** No common misspellings detected (AI will do a full review)\n")

        if check_type in ("grammar", "all"):
            issues = []

            if re.search(r'\bi\b', text) and not re.search(r'\bI\b', text[:50]):
                pass

            if re.search(r'[a-z]\?[a-z]', text):
                issues.append("Possible missing space after question mark")
            if re.search(r'[a-z]\![a-z]', text):
                issues.append("Possible missing space after exclamation mark")
            if re.search(r'\s,\s', text):
                issues.append("Space before comma found")
            if re.search(r',[^\s]', text):
                issues.append("Missing space after comma")

            contractions = {
                "dont": "don't", "cant": "can't", "wont": "won't", "isnt": "isn't",
                "arent": "aren't", "wasnt": "wasn't", "werent": "weren't", "hasnt": "hasn't",
                "havent": "haven't", "hadnt": "hadn't", "doesnt": "doesn't", "didnt": "didn't",
                "couldnt": "couldn't", "wouldnt": "wouldn't", "shouldnt": "shouldn't",
                "its ": "its ", "theres": "there's", "theyre": "they're", "youre": "you're",
                "whos": "who's", "whats": "what's", "thats": "that's",
            }
            for wrong, correct in contractions.items():
                if wrong in text.lower().split():
                    issues.append(f"'{wrong}' -> '{correct}' (missing apostrophe)")

            if issues:
                parts.append(f"\n**Grammar/Punctuation Issues:**\n")
                for issue in issues:
                    parts.append(f"- {issue}\n")

        parts.append(f"\n**AI Review:** [The AI will now provide a detailed review of the text in its response, including specific corrections and suggestions.]")

        return "".join(parts)


class RephraseTool(Tool):
    name = "rephrase"
    description = "Rephrase or rewrite text with a different tone, style, or for a different audience. Use for improving writing clarity, adjusting formality, simplifying complex text, or adapting content for different contexts."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to rephrase or rewrite.",
            },
            "style": {
                "type": "string",
                "enum": [
                    "simpler", "more_formal", "more_casual", "more_professional",
                    "more_persuasive", "more_concise", "more_detailed",
                    "academic", "creative", "neutral",
                ],
                "description": "The desired style for the rewritten text.",
            },
            "audience": {
                "type": "string",
                "description": "Target audience (e.g. 'general public', 'experts', 'children', 'executives', 'students').",
            },
        },
        "required": ["text", "style"],
    }

    def execute(self, text: str, style: str, audience: str = "") -> str:
        if not text.strip():
            return "No text provided to rephrase."

        word_count = len(text.split())
        audience_str = f" for {audience}" if audience else ""

        return (
            f"**Rephrase Request:**\n"
            f"- **Style:** {style.replace('_', ' ').title()}{audience_str}\n"
            f"- **Original length:** {word_count} words\n\n"
            f"**Original text:**\n{text}\n\n"
            f"**[The AI will now rewrite this text in a {style.replace('_', ' ')} style{audience_str} in its response.]**"
        )
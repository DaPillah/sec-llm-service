from html.parser import HTMLParser
from re import sub #regular expressions op

class FilingTextExtractor(HTMLParser):
    def __init__(self, max_tokens):
        super().__init__()
        self.max_tokens = max_tokens 
        self.tags = {"pg_break": set(["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]),
                     "row_break": set(["tr"]),
                     "cell_break": set(["td", "th"]),
                     } 
        self.skip_tag = set(["style", "script", "ix:header", "ix:hidden", "ix:references", "ix:resources"])
        self.skip_content = False
        self.output = ""

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tag:
            self.skip_content = True

    def handle_endtag(self, tag):
        if tag in self.skip_tag:
            self.skip_content = False

        if not self.skip_content:
            if tag in self.tags["pg_break"]:
                self.output += "\n\n"
            elif tag in self.tags["row_break"]:
                self.output += "\n"
            elif tag in self.tags["cell_break"]:
                self.output += " "
            # else: inline/XBRL tag, no whitespace added 

    def handle_data(self, data):
        if not self.skip_content:
            self.output += data
        
    def get_text(self):
        """normalize whitespace"""
        # Collapse runs of spaces/tabs into a single space, w/ exclusion of xa0
        fix = sub(r"[\t\xa0 ]+", " ", self.output)

        # Strip leading/trailing whitespace from every line
        strip = "\n".join(line.strip() for line in fix.split("\n"))

        # Collapse 3+ consecutive newlines (now-empty lines included) down to
        # exactly \n\n, so paragraph boundaries stay well-defined for splitting later
        result = sub(r"\n{3,}", "\n\n", strip)


        """truncate to budget, preserving paragraph boundaries"""
        parts = result.split("\n\n")
        count = 0
        para_list = []
        for paragraph in parts:
            length = len(paragraph) / 4
            if count + length >= self.max_tokens:
                break
            count += length
            para_list.append(paragraph)

        """Fallback: first paragraph alone exceeds budget"""
        if not para_list and parts:
            raw_sentences = parts[0].split(". ")
            # re-attach the period to every sentence except possibly the last
            sentences = [s + "." if not s.endswith(".") else s for s in raw_sentences if s]

            count = 0
            for sentence in sentences:
                length = len(sentence) / 4
                if count + length >= self.max_tokens:
                    break
                count += length
                para_list.append(sentence)

        return "\n\n".join(para_list)

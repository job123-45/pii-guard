import re

PATTERNS = {
 "EMAIL": (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I), .99),
 "PHONE": (re.compile(r"(?<!\w)(?:\+?1[ .-]?)?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?!\w)"), .91),
 "EMPLOYEE_ID": (re.compile(r"\b(?:employee|emp|staff)[ _-]?(?:id|no\.?|number)\b\s*[:#-]?\s*(?P<value>[A-Z0-9-]{4,})\b",re.I), .94),
 "ACCOUNT_NUMBER": (re.compile(r"\b(?:account|acct)[ _-]?(?:number|no\.?|#)\s*[:#-]?\s*(?P<value>[0-9][0-9 -]{5,18})\b",re.I), .93),
 "GOVERNMENT_ID": (re.compile(r"\b(?:SSN|social security(?: number)?|tax id)\s*[:#-]?\s*(?P<value>\d{3}-?\d{2}-?\d{4})\b",re.I), .99),
 "ADDRESS": (re.compile(r"\b(?:address|home address|mailing address)\s*[:#-]\s*[^\n,;]{5,70}(?:,\s*[^\n;]{2,40})?",re.I), .78),
}

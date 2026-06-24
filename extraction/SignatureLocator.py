import pdfplumber

# Words/phrases that show up clustered together almost only on signature
# pages. We're not trying to be clever here — just counting hits is enough
# to tell a signature page apart from a normal contract page, and it's
# free/fast compared to a vision model call.
SIGNATURE_KEYWORDS = [
    "in witness whereof",
    "signature:",
    "signed:",
    "authorized representative",
    "authorized signatory",
    "/s/",
    "docusign envelope id",
    "by:",
    "title:",
    "name:",
    "date:",
]

# How many points a page needs before we're confident it's the signature
# page, and how many pages from the end we're willing to look at before
# giving up and just guessing the last page.
SCORE_THRESHOLD = 3
SEARCH_WINDOW = 8


def _score_page(text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in SIGNATURE_KEYWORDS if keyword in lowered)


def find_signature_page(file_path: str) -> int:
    """
    Returns the page number (1-indexed) most likely to contain signatures.
    Searches backward from the last page since signature blocks are almost
    always near the end of a contract — this way we usually find it after
    reading just 1-2 pages instead of the whole document.
    """
    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        start = max(0, total_pages - SEARCH_WINDOW)

        # range(total_pages - 1, start - 1, -1) walks backward: last page,
        # second-to-last, etc., stopping once we've checked SEARCH_WINDOW pages.
        for page_index in range(total_pages - 1, start - 1, -1):
            text = pdf.pages[page_index].extract_text() or ""
            if _score_page(text) >= SCORE_THRESHOLD:
                return page_index + 1  # convert back to 1-indexed

        # nothing scored high enough — best guess is still the last page
        return total_pages

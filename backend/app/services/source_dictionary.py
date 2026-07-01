from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEntry:
    label: str
    value: str
    note: str


ARCHIVE_QUERY_SOURCES: tuple[SourceEntry, ...] = (
    SourceEntry("General presentations", "presentation", "Broad Archive.org PowerPoint search."),
    SourceEntry("Lecture slides", "lecture slides", "Academic slide decks and course material."),
    SourceEntry("Training presentations", "training presentation", "Training decks, workshops, and tutorials."),
    SourceEntry("Business presentations", "business presentation", "Business, operations, and management decks."),
    SourceEntry("Education presentations", "education presentation", "Teaching and classroom decks."),
    SourceEntry("Workshop presentations", "workshop presentation", "Workshop and seminar materials."),
    SourceEntry("Conference presentations", "conference presentation", "Conference and event slide decks."),
    SourceEntry("Science presentations", "science presentation", "Science education and research presentations."),
    SourceEntry("Engineering slides", "engineering lecture slides", "Engineering lectures and technical decks."),
    SourceEntry("Computer science slides", "computer science lecture slides", "CS lectures and technical teaching slides."),
    SourceEntry("Healthcare presentations", "healthcare training presentation", "Health and public-health training decks."),
    SourceEntry("Cybersecurity presentations", "cybersecurity training presentation", "Security awareness and technical training."),
    SourceEntry("Marketing presentations", "marketing presentation", "Marketing, sales, and communications decks."),
    SourceEntry("Government training", "government training presentation", "Public-sector training and policy decks."),
    SourceEntry("Open education", "open educational resources powerpoint", "OER-focused slide decks."),
)


CRAWL_SEED_SOURCES: tuple[SourceEntry, ...] = (
    SourceEntry("MIT OpenCourseWare", "https://ocw.mit.edu/", "Open course material with slide resources."),
    SourceEntry("OER Commons PowerPoint", "https://oercommons.org/browse?f.keyword=powerpoint", "Open educational resources tagged PowerPoint."),
    SourceEntry("OER Commons Slides", "https://oercommons.org/browse?f.keyword=slides", "Open educational resources tagged slides."),
    SourceEntry("MERLOT", "https://www.merlot.org/", "Curated open teaching and learning materials."),
    SourceEntry("SkillsCommons", "https://www.skillscommons.org/", "Open workforce training resources."),
    SourceEntry("CDC", "https://www.cdc.gov/", "Public health training and education materials."),
    SourceEntry("EPA", "https://www.epa.gov/", "Public environmental education and training materials."),
    SourceEntry("NASA", "https://www.nasa.gov/", "Public science and education resources."),
    SourceEntry("FEMA", "https://www.fema.gov/", "Emergency-management training resources."),
    SourceEntry("GSA SmartPay", "https://smartpay.gsa.gov/", "Government training slide materials."),
)


def source_dictionary_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "archive_queries": [entry.__dict__ for entry in ARCHIVE_QUERY_SOURCES],
        "crawl_seed_urls": [entry.__dict__ for entry in CRAWL_SEED_SOURCES],
    }

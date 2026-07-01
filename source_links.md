# PPT/PPTX Source Dictionary

Use this file as the visible list of places/queries to pull PPT and PPTX files from.
Prefer public, open, educational, or government sources. The app should still dedupe by
canonical URL and SHA-256, filter Chinese-language decks, and skip low-image PPTX files.

## Filter Audit

Checked against `backend/app/services/content_filters.py`:

```text
URLs checked: 33
Allowed: 33
Blocked domains: 0
Chinese-flagged URLs/domains: 0
```

The backend also rejects future source-dictionary entries that match the blocklist,
Chinese-language signals, or `.cn` Chinese domains before starting crawler runs.

## Archive.org Search Queries

These are not direct links. They are search phrases for Archive.org's PowerPoint metadata.

```text
presentation
lecture slides
training presentation
business presentation
education presentation
workshop presentation
conference presentation
science presentation
engineering lecture slides
computer science lecture slides
healthcare training presentation
cybersecurity training presentation
marketing presentation
government training presentation
open educational resources powerpoint
public health training presentation
professional development presentation
teacher training powerpoint
student workshop slides
management training presentation
```

## Crawl Seed Pages

These are broad pages/domains the crawler can visit to find PPT/PPTX links.

| Source | URL | Notes |
| --- | --- | --- |
| MIT OpenCourseWare | https://ocw.mit.edu/ | Open course pages, many lecture-slide resource pages. |
| MIT OCW AI 101 | https://ocw.mit.edu/courses/res-6-013-ai-101-fall-2021/pages/supporting-materials/ | Includes a PPTX slide deck resource. |
| MIT OCW Learning, Media, and Technology | https://ocw.mit.edu/courses/cms-595-learning-media-and-technology-spring-2024/lists/lecture-slides/ | Lecture slides available in PowerPoint and PDF. |
| MIT OCW Network Optimization | https://ocw.mit.edu/courses/15-082j-network-optimization-fall-2010/pages/lecture-notes/ | Lecture notes include PPT versions. |
| MIT OCW Theory of Computation | https://ocw.mit.edu/courses/18-404j-theory-of-computation-fall-2020/pages/lecture-notes/ | Lecture notes include PPT links. |
| OER Commons PowerPoint | https://oercommons.org/browse?f.keyword=powerpoint | OER pages tagged PowerPoint. |
| OER Commons Powerpoints | https://oercommons.org/browse?f.keyword=powerpoints | OER pages tagged Powerpoints. |
| OER Commons Slides | https://oercommons.org/browse?f.keyword=slides | OER pages tagged slides. |
| OER Commons Open Educational Resource | https://oercommons.org/browse?f.keyword=open-educational-resource | OER materials, some include slide decks. |
| Open Oregon OER Group | https://oercommons.org/groups/open-oregon-educational-resources/425/18708/ | Open Oregon resources with PowerPoint presentations. |
| CDC Project Firstline | https://www.cdc.gov/project-firstline/ | Public health training materials with slide decks. |
| CDC Public Health 101 | https://www.cdc.gov/training-publichealth101/ | Public health training decks. |
| GSA SmartPay | https://smartpay.gsa.gov/ | Government travel/payment training decks. |
| MERLOT | https://www.merlot.org/ | Open teaching and learning materials. |
| SkillsCommons | https://www.skillscommons.org/ | Open workforce training resources. |
| NASA | https://www.nasa.gov/ | Public science and education resources. |
| EPA | https://www.epa.gov/ | Public environmental education/training resources. |
| FEMA | https://www.fema.gov/ | Emergency-management training resources. |

## Direct PPT/PPTX Examples

These are confirmed direct PPT/PPTX URLs that can be added manually or used as test links.

| Source | URL | Notes |
| --- | --- | --- |
| CDC Project Firstline Topic 1 | https://www.cdc.gov/project-firstline/media/ppts/PFL-T1-60min-Slides.pptx | Infection control training. |
| CDC Project Firstline Topic 2 | https://www.cdc.gov/project-firstline/media/ppts/PFL-T2-20min-Slides.pptx | Basic science of viruses. |
| CDC Project Firstline Topic 3 | https://www.cdc.gov/project-firstline/media/ppts/PFL-T3-60min-Slides.pptx | Respiratory droplets training. |
| CDC Project Firstline Topic 8 | https://www.cdc.gov/project-firstline/media/ppts/PFL-T8-60min-Slides.pptx | PPE gloves and gowns. |
| CDC Project Firstline Hand Hygiene | https://www.cdc.gov/project-firstline/media/ppts/PFL-T9-10min-Slides.pptx | Hand hygiene training. |
| CDC Public Health 101 Epidemiology | https://www.cdc.gov/training-publichealth101/media/pptx/introduction-to-epidemiology.pptx | Public health training. |
| CDC Professional Development 101 | https://archive.cdc.gov/www_cdc_gov/healthyschools/tths/Slides-PD101-Part-1_1733163871.pptx | Professional development training. |
| GSA Travel Management Essentials | https://smartpay.gsa.gov/files/GSA007_GSA_SmartPay_Travel_Management_Essentials.pptx | Government travel card training. |
| GSA Data Analytics Oversight | https://smartpay.gsa.gov/files/GSA010_Use_of_Data_Analytics_for_Effective_Program_Oversight.pptx | Program oversight training. |
| GSA Federal Travel and Ethics | https://smartpay.gsa.gov/files/GSA019_Federal_Travel_and_Ethics.pptx | Federal travel/ethics training. |
| GSA Fleet Offerings | https://smartpay.gsa.gov/files/GSA022_GSA_Fleet_Offerings.pptx | Fleet training material. |
| GSA DoD Travel Card Update | https://smartpay.gsa.gov/files/GSA024_DoD_Travel_Card_Program_Update.pptx | DoD travel-card update. |
| TCSG OER Training | https://www.tcsg.edu/wp-content/uploads/2020/10/Identifying-Open-Educational-Resources-10.14.20.pptx | Open educational resources training. |
| Miami Ohio Copyright and OER | https://copyrightconference.lib.miamioh.edu/wp-content/uploads/2017/08/CopyrightandOER_MULCC2017_v2.pptx | OER/copyright presentation. |
| UMass Boston Open Ed Week | https://www.umb.edu/media/umassboston/content-assets/learningdesign/Open_Education_Resources_-_Open_Week_-_Mar_8_-_rev5.pptx | Open education presentation. |

## Suggested Manual Batch

Paste these into the app's link box or send to `/api/documents/manual-links`.

```text
https://ocw.mit.edu/
https://ocw.mit.edu/courses/cms-595-learning-media-and-technology-spring-2024/lists/lecture-slides/
https://ocw.mit.edu/courses/18-404j-theory-of-computation-fall-2020/pages/lecture-notes/
https://oercommons.org/browse?f.keyword=powerpoint
https://oercommons.org/browse?f.keyword=slides
https://www.cdc.gov/project-firstline/
https://www.cdc.gov/training-publichealth101/
https://smartpay.gsa.gov/
https://www.cdc.gov/project-firstline/media/ppts/PFL-T1-60min-Slides.pptx
https://www.cdc.gov/project-firstline/media/ppts/PFL-T2-20min-Slides.pptx
https://www.cdc.gov/project-firstline/media/ppts/PFL-T3-60min-Slides.pptx
https://www.cdc.gov/project-firstline/media/ppts/PFL-T8-60min-Slides.pptx
https://www.cdc.gov/project-firstline/media/ppts/PFL-T9-10min-Slides.pptx
https://www.cdc.gov/training-publichealth101/media/pptx/introduction-to-epidemiology.pptx
https://smartpay.gsa.gov/files/GSA007_GSA_SmartPay_Travel_Management_Essentials.pptx
https://smartpay.gsa.gov/files/GSA010_Use_of_Data_Analytics_for_Effective_Program_Oversight.pptx
https://smartpay.gsa.gov/files/GSA019_Federal_Travel_and_Ethics.pptx
https://smartpay.gsa.gov/files/GSA022_GSA_Fleet_Offerings.pptx
https://smartpay.gsa.gov/files/GSA024_DoD_Travel_Card_Program_Update.pptx
```

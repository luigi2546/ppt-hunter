# PPT/PPTX Source Dictionary

Use this file as the visible list of places/queries to pull PPT and PPTX files from.
Prefer public, open, educational, or government sources. The app should still dedupe by
canonical URL and SHA-256, filter Chinese-language decks, and skip low-image PPTX files.

## Filter Audit

Checked against `backend/app/services/content_filters.py`:

```text
URLs checked: 55
Allowed: 55
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
safety training presentation
OSHA training powerpoint
energy training presentation
public health lecture slides
nursing lecture slides
data science lecture slides
statistics lecture slides
workplace software skills powerpoint
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
| OSHA | https://www.osha.gov/ | Workplace safety training materials. |
| Energy.gov | https://www.energy.gov/ | Energy and workforce training resources. |
| EERE Exchange | https://eere-exchange.energy.gov/ | Energy efficiency and renewable energy resources. |
| OpenStax | https://openstax.org/ | Open textbook pages and OER hubs. |
| OpenStax OER Commons Hub | https://oercommons.org/hubs/OpenStax | OpenStax-aligned OER community materials. |
| OpenStax Psychology 2e | https://openstax.org/details/books/psychology-2e | Open textbook page with instructor resources references. |
| OpenStax Concepts of Biology | https://openstax.org/details/books/concepts-biology | Open textbook page with teaching resources references. |
| OpenStax Medical-Surgical Nursing | https://openstax.org/books/medical-surgical-nursing/pages/preface | Mentions PowerPoint lecture slides in resources. |

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
| OSHA Train-the-Trainer | https://www.osha.gov/sites/default/files/2018-12/fy15_sh-27662-sh5_PSM_Train_the_Trainer.pptx | Safety training slide deck. |
| OSHA Adult Learners | https://www.osha.gov/sites/default/files/2018-12/fy11_sh-22311-11_Mod5-TrainingAdultLearners.pptx | Training-adult-learners slide deck. |
| OSHA Safety Committees | https://www.osha.gov/sites/default/files/2018-11/fy10_sh-20839-10_hs_committees_part1.pptx | Workplace safety committee training. |
| OSHA Lockout Tagout | https://www.osha.gov/sites/default/files/2022-04/Lock%20Out%20Tag%20Out%20Hazardous%20Energy%20Control.pptx | Hazardous energy control training. |
| OSHA Hazard Communication Refresher | https://www.osha.gov/sites/default/files/2019-04/HCS2012-GHS-Refresher.pptx | Hazard communication refresher. |
| OSHA Orientation | https://www.osha.gov/sites/default/files/2018-12/fy11_sh-22300-11_OSHAOrientation.pptx | OSHA orientation training. |
| OSHA Healthcare ETS Training | https://www.osha.gov/sites/default/files/COVID-19%20Healthcare%20ETS%20502%20Employee%20Training.pptx | COVID-19 healthcare ETS training. |
| OSHA Personal Protective Equipment | https://www.osha.gov/sites/default/files/2022-04/Personal%20Protective%20Equipment%20.pptx | PPE training deck. |
| OSHA Chemical Safety Training | https://www.osha.gov/sites/default/files/2022-01/Chemical%20Safety%20Training.pptx | Chemical safety training deck. |
| OSHA Ladder Safety | https://www.osha.gov/sites/default/files/2022-04/Ladder%20Safety.pptx | Ladder safety training deck. |
| Energy.gov TCF Briefing | https://www.energy.gov/sites/prod/files/2019/09/f66/TCF%20Briefing%20Sep%2010%20IP%20Counsel.pptx | Technology/commercialization briefing. |
| EERE Heat Pump Sales | https://bsesc.energy.gov/sites/default/files/Heat%20Pump%20Sales%20-%20Presentation.pptx | Energy workforce sales training. |
| EERE Impact and EJ Analysis | https://www1.eere.energy.gov/iedo/downloads/2023/peer_review/Dollinger_IEDO_Strategic-Analysis_Poster_Project-and-Portfolio-Impact-and-Environmental-Justice-Analysis.pptx | Energy analysis presentation. |
| EERE Targeted Extraction | https://www1.eere.energy.gov/iedo/downloads/2023/peer_review/Jassby_AMMTO_Targeted%20Extraction%20of%20Valuable%20Intermediate%20Products.pptx | Energy technology presentation. |

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
https://www.osha.gov/
https://www.energy.gov/
https://eere-exchange.energy.gov/
https://openstax.org/
https://oercommons.org/hubs/OpenStax
https://www.osha.gov/sites/default/files/2018-12/fy15_sh-27662-sh5_PSM_Train_the_Trainer.pptx
https://www.osha.gov/sites/default/files/2018-12/fy11_sh-22311-11_Mod5-TrainingAdultLearners.pptx
https://www.osha.gov/sites/default/files/2022-04/Lock%20Out%20Tag%20Out%20Hazardous%20Energy%20Control.pptx
https://www.osha.gov/sites/default/files/2019-04/HCS2012-GHS-Refresher.pptx
https://www.osha.gov/sites/default/files/2022-04/Personal%20Protective%20Equipment%20.pptx
https://www.osha.gov/sites/default/files/2022-01/Chemical%20Safety%20Training.pptx
https://www.osha.gov/sites/default/files/2022-04/Ladder%20Safety.pptx
https://www.energy.gov/sites/prod/files/2019/09/f66/TCF%20Briefing%20Sep%2010%20IP%20Counsel.pptx
https://bsesc.energy.gov/sites/default/files/Heat%20Pump%20Sales%20-%20Presentation.pptx
```

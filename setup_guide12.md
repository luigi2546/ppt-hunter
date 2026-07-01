# PowerPoint Collection Setup Guide
## Complete Instructions for Node 2

---

## OVERVIEW

You are setting up a second independent collection node. This node will:
- Download PowerPoint files (PPT/PPTX) from Internet Archive
- Store them in your own AWS S3 bucket
- Display them on a web portal for the client to download
- Run automatically until July 3, 2026

**Your node collects files independently. No connection to Node 1 needed.**

---

## WHAT YOU NEED

- A computer (Mac or Windows)
- An AWS account (new or existing)
- About 60 minutes to set up

---

## PART 1: AWS ACCOUNT SETUP

### Step 1.1: Create AWS Account
1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the signup steps
4. You will need a credit card but will NOT be charged (free tier)
5. Wait for account activation (usually instant, sometimes 24 hours)

### Step 1.2: Create IAM User
1. Log into AWS Console at https://console.aws.amazon.com
2. Search for "IAM" in the top search bar
3. Click "Users" on the left sidebar
4. Click "Create user"
5. Username: `scraper-user`
6. Click "Next"
7. Select "Attach policies directly"
8. Search for and check these policies:
   - `AmazonS3FullAccess`
   - `CloudFrontFullAccess`
9. Click "Next" then "Create user"
10. Click on the new user "scraper-user"
11. Click "Security credentials" tab
12. Click "Create access key"
13. Select "Command Line Interface (CLI)"
14. Check the confirmation box
15. Click "Next" then "Create access key"
16. **COPY BOTH KEYS - YOU WILL NEED THEM LATER:**
    - Access key ID: `AKIA...`
    - Secret access key: `...`

### Step 1.3: Create S3 Bucket
1. Go to AWS Console → S3
2. Click "Create bucket"
3. Bucket name: `research-documents-node2`
4. Region: `eu-north-1` (Europe Stockholm)
5. Uncheck "Block all public access"
6. Check the confirmation box
7. Leave everything else as default
8. Click "Create bucket"

### Step 1.4: Make S3 Bucket Public
1. Click on your new bucket `research-documents-node2`
2. Click "Permissions" tab
3. Scroll to "Bucket policy"
4. Click "Edit"
5. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::research-documents-node2",
                "arn:aws:s3:::research-documents-node2/*"
            ]
        }
    ]
}
```

6. Click "Save changes"

### Step 1.5: Enable S3 Static Website Hosting
1. Still on your bucket, click "Properties" tab
2. Scroll to bottom → "Static website hosting"
3. Click "Edit"
4. Select "Enable"
5. Index document: `index.html`
6. Click "Save changes"

### Step 1.6: Add CORS Policy
1. Click "Permissions" tab
2. Scroll to "Cross-origin resource sharing (CORS)"
3. Click "Edit"
4. Paste this:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

5. Click "Save changes"

---

## PART 2: EC2 SERVER SETUP

### Step 2.1: Launch EC2 Instance
1. Go to AWS Console → EC2
2. Click "Launch instance"
3. Name: `ppt-scraper-node2`
4. Under "Application and OS Images":
   - Select "Ubuntu" (NOT Amazon Linux)
   - Version: Ubuntu Server 22.04 LTS
5. Instance type: `t3.small`
6. Key pair: Click "Create new key pair"
   - Name: `node2-key`
   - Type: RSA
   - Format: .pem
   - Click "Create key pair"
   - **SAVE THE .pem FILE - YOU CANNOT GET IT AGAIN**
7. Network settings: Leave defaults (allow SSH)
8. Storage: 20 GB (change from default 8GB)
9. Click "Launch instance"

### Step 2.2: Connect to EC2
Wait 2 minutes for instance to start, then:

**On Mac:**
```bash
# Open Terminal
# Go to folder where you saved node2-key.pem
cd ~/Downloads

# Fix key permissions
chmod 400 node2-key.pem

# Get your EC2 IP from AWS Console → EC2 → Instances
# Look for "Public IPv4 address"

# Connect (replace IP_ADDRESS with your actual IP)
ssh -i node2-key.pem ubuntu@IP_ADDRESS
```

**On Windows:**
- Use PuTTY or Windows Terminal
- Convert .pem to .ppk using PuTTYgen
- Connect using PuTTY

---

## PART 3: INSTALL SOFTWARE

Run these commands one by one after connecting to EC2:

```bash
# Update system
sudo apt update
sudo apt install -y python3-pip python3-venv jq

# Create project folder
mkdir -p /home/ubuntu/ppt-scraper
cd /home/ubuntu/ppt-scraper

# Create Python environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install internetarchive boto3 python-pptx langdetect requests

# Configure AWS credentials
aws configure
```

When `aws configure` asks:
```
AWS Access Key ID: PASTE_YOUR_ACCESS_KEY_HERE
AWS Secret Access Key: PASTE_YOUR_SECRET_KEY_HERE
Default region name: eu-north-1
Default output format: json
```

---

## PART 4: CREATE THE SCRIPTS

### Step 4.1: Create Fortune 500 Blocklist

```bash
cat > /home/ubuntu/ppt-scraper/blocked_fortune500_domains.txt << 'EOF'
walmart.com
amazon.com
apple.com
unitedhealthgroup.com
berkshirehathaway.com
cvshealth.com
exxonmobil.com
alphabet.com
google.com
microsoft.com
jpmorganchase.com
bankofamerica.com
coca-colacompany.com
pepsico.com
meta.com
tesla.com
ford.com
gm.com
boeing.com
disney.com
att.com
chevron.com
cigna.com
comcast.com
conocophillips.com
deere.com
delta.com
fedex.com
ge.com
goldmansachs.com
homedepot.com
honeywell.com
hp.com
ibm.com
intel.com
johnsonandjohnson.com
jpmorgan.com
lockheedmartin.com
lowes.com
mckesson.com
merck.com
metlife.com
morganstanley.com
nike.com
oracle.com
pfizer.com
proctergamble.com
raytheon.com
starbucks.com
target.com
unitedhealth.com
ups.com
verizon.com
visa.com
walgreens.com
wellsfargo.com
EOF
```

### Step 4.2: Create Main Scraper Script

```bash
nano /home/ubuntu/ppt-scraper/ia_scraper.py
```

Paste the entire script below, then press `Ctrl+X`, then `Y`, then `Enter` to save:

```python
# ============================================================
# INTERNET ARCHIVE POWERPOINT SCRAPER v1.1
# Node 2 - Independent Collection
# Target: 200,000 PPT/PPTX files
# Storage: AWS S3 (research-documents-node2)
# ============================================================

import os
import io
import json
import time
import hashlib
import sqlite3
import logging
import threading
import traceback
from datetime import datetime
from urllib.parse import urlparse

import boto3
import requests
from internetarchive import search_items, get_item
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

try:
    from langdetect import detect as detect_language
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================
BUCKET = 'research-documents-node2'
REGION = 'eu-north-1'
START_DATE = datetime(2026, 6, 28)
TOTAL_DAYS = 7
MAX_WORKERS = 30
MIN_FILE_SIZE = 102400
MAX_FILE_SIZE = 104857600
MIN_SLIDES = 5
DELAY_BETWEEN_ITEMS = 0.5
DELAY_BETWEEN_FILES = 0.2
MAX_RETRIES = 1
ITEM_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60
DB_PATH = '/home/ubuntu/ppt-scraper/ia_scraper.db'
LOG_PATH = '/home/ubuntu/ppt-scraper/ia_scraper.log'
SCRATCH_DIR = '/home/ubuntu/ppt-scraper/scratch'
FORTUNE500_FILE = '/home/ubuntu/ppt-scraper/blocked_fortune500_domains.txt'

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ============================================================
# EXCLUSION LISTS
# ============================================================
IVY_LEAGUE_DOMAINS = [
    'harvard.edu', 'yale.edu', 'princeton.edu', 'columbia.edu',
    'brown.edu', 'dartmouth.edu', 'cornell.edu', 'upenn.edu',
]

IVY_LEAGUE_KEYWORDS = [
    'harvard', 'yale', 'princeton', 'columbia university',
    'brown university', 'dartmouth', 'cornell',
    'university of pennsylvania', 'upenn', 'wharton',
]

CHINESE_LANG_CODES = [
    'zh', 'zho', 'chi', 'cmn', 'chinese', 'mandarin',
    '中文', '普通话', '國語', '汉语', '漢語',
]

SEARCH_QUERIES = [
    'pptx presentation slides',
    'powerpoint presentation business',
    'ppt slides education',
    'powerpoint training slides',
    'pptx lecture slides',
    'powerpoint marketing presentation',
    'ppt data analysis slides',
    'powerpoint conference presentation',
    'pptx workshop slides',
    'powerpoint seminar presentation',
    'ppt technology slides',
    'powerpoint health presentation',
    'pptx science slides',
    'powerpoint economics presentation',
    'ppt management slides',
    'powerpoint research presentation',
    'pptx engineering slides',
    'powerpoint finance presentation',
    'ppt medical slides',
    'powerpoint government presentation',
    'pptx annual report slides',
    'powerpoint strategy presentation',
    'ppt human resources slides',
    'powerpoint sales presentation',
    'pptx project management slides',
]

# ============================================================
# LOAD FORTUNE 500 BLOCKLIST
# ============================================================
def load_fortune500_blocklist():
    blocked = set()
    if os.path.exists(FORTUNE500_FILE):
        with open(FORTUNE500_FILE, 'r') as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith('#'):
                    blocked.add(line)
    log.info(f"Loaded {len(blocked)} Fortune 500 domains")
    return blocked

FORTUNE500_DOMAINS = load_fortune500_blocklist()

# ============================================================
# DATABASE
# ============================================================
db_lock = threading.Lock()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_identifier TEXT,
            archive_item_url TEXT,
            file_name TEXT,
            file_extension TEXT,
            file_size INTEGER,
            download_url TEXT UNIQUE,
            source_domain TEXT,
            s3_path TEXT,
            license_or_rights TEXT,
            language_metadata TEXT,
            language_detected TEXT,
            blocked_reason TEXT,
            status TEXT DEFAULT "discovered",
            attempt_count INTEGER DEFAULT 0,
            last_error TEXT,
            sha256_hash TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_status ON files(status)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_download_url ON files(download_url)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sha256 ON files(sha256_hash)')
    conn.commit()
    conn.close()
    log.info("Database initialized")

def db_execute(query, params=()):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(query, params)
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

def db_fetchone(query, params=()):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        row = c.fetchone()
        conn.close()
        return row

def db_fetchall(query, params=()):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows

def db_update_status(download_url, status, error=None, s3_path=None,
                     sha256=None, lang_detected=None, blocked_reason=None):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE files SET
                status=?, last_error=?, s3_path=?,
                sha256_hash=?, language_detected=?,
                blocked_reason=?, attempt_count=attempt_count+1,
                updated_at=?
            WHERE download_url=?
        ''', (
            status, error, s3_path, sha256,
            lang_detected, blocked_reason,
            datetime.now().isoformat(), download_url
        ))
        conn.commit()
        conn.close()

# ============================================================
# S3
# ============================================================
s3_client = boto3.client('s3', region_name=REGION)

def get_day_folder():
    days_elapsed = (datetime.now() - START_DATE).days + 1
    days_elapsed = max(1, min(days_elapsed, TOTAL_DAYS))
    return f"collection_02_presentations/day_{days_elapsed:03d}"

def upload_to_s3(local_path, s3_key, metadata=None):
    extra_args = {
        'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
    if metadata:
        clean_meta = {str(k)[:128]: str(v)[:1024] for k, v in metadata.items()}
        extra_args['Metadata'] = clean_meta
    s3_client.upload_file(local_path, BUCKET, s3_key, ExtraArgs=extra_args)

def upload_json_to_s3(data, s3_key):
    s3_client.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=2, default=str).encode('utf-8'),
        ContentType='application/json'
    )

def upload_log_to_s3():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_client.upload_file(
            LOG_PATH, BUCKET,
            f"ia-ppt-project/logs/ia_scraper_{timestamp}.log"
        )
    except Exception as e:
        log.error(f"Failed to upload log: {e}")

def upload_db_to_s3():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_client.upload_file(
            DB_PATH, BUCKET,
            f"ia-ppt-project/inventory/ia_scraper_{timestamp}.db"
        )
        log.info("DB backed up to S3")
    except Exception as e:
        log.error(f"Failed to upload DB: {e}")

# ============================================================
# FILTERING
# ============================================================
def is_ivy_league(text):
    if not text:
        return False
    text_lower = text.lower()
    for d in IVY_LEAGUE_DOMAINS:
        if d in text_lower:
            return True
    for k in IVY_LEAGUE_KEYWORDS:
        if k in text_lower:
            return True
    return False

def is_fortune500(text):
    if not text:
        return False
    text_lower = text.lower()
    for d in FORTUNE500_DOMAINS:
        if d in text_lower:
            return True
    return False

def is_chinese(text):
    if not text:
        return False
    text_lower = text.lower()
    for c in CHINESE_LANG_CODES:
        if c in text_lower:
            return True
    return False

def check_filters(text):
    if is_ivy_league(text):
        return False, 'skipped_ivy_league'
    if is_fortune500(text):
        return False, 'skipped_fortune500'
    if is_chinese(text):
        return False, 'skipped_chinese_mandarin'
    return True, None

# ============================================================
# QUALITY CHECK
# ============================================================
def check_pptx_quality(local_path):
    try:
        prs = Presentation(local_path)
        slide_count = len(prs.slides)

        if slide_count < MIN_SLIDES:
            return False, {}, f"Too few slides: {slide_count}"

        total_images = 0
        total_charts = 0
        slides_with_visuals = 0

        for slide in prs.slides:
            slide_has_visual = False
            try:
                for shape in slide.shapes:
                    try:
                        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                            total_images += 1
                            slide_has_visual = True
                        elif shape.shape_type == MSO_SHAPE_TYPE.CHART:
                            total_charts += 1
                            slide_has_visual = True
                        elif shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                            total_images += 1
                            slide_has_visual = True
                    except:
                        continue
            except:
                continue
            if slide_has_visual:
                slides_with_visuals += 1

        metadata = {
            'slide_count': slide_count,
            'image_count': total_images,
            'chart_count': total_charts,
            'slides_with_visuals': slides_with_visuals,
            'visual_density': round(
                slides_with_visuals / slide_count, 2
            ) if slide_count > 0 else 0,
        }

        try:
            props = prs.core_properties
            metadata['title'] = props.title or ''
            metadata['author'] = props.author or ''
            metadata['organization'] = props.company or ''
            metadata['creation_date'] = str(props.created or '')
            metadata['modification_date'] = str(props.modified or '')
            metadata['description'] = props.description or ''
            metadata['keywords'] = props.keywords or ''
        except:
            pass

        return True, metadata, "Passed"

    except Exception as e:
        return False, {}, f"Error reading PPTX: {e}"

def detect_lang_from_pptx(local_path):
    if not LANGDETECT_AVAILABLE:
        return None
    try:
        prs = Presentation(local_path)
        text_chunks = []
        for slide in prs.slides[:5]:
            for shape in slide.shapes:
                try:
                    if hasattr(shape, 'text') and shape.text.strip():
                        text_chunks.append(shape.text.strip())
                except:
                    continue
        combined = ' '.join(text_chunks)[:1000]
        if len(combined) < 20:
            return None
        return detect_language(combined)
    except:
        return None

# ============================================================
# SHA256
# ============================================================
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

# ============================================================
# PROCESS ONE FILE
# ============================================================
def process_file(identifier, file_name, file_size, download_url,
                 license_rights, lang_meta):

    file_ext = os.path.splitext(file_name)[1].lower()
    local_path = os.path.join(
        SCRATCH_DIR,
        f"{hashlib.md5(download_url.encode()).hexdigest()}{file_ext}"
    )

    if file_size < MIN_FILE_SIZE:
        db_update_status(download_url, 'skipped_too_large',
                        blocked_reason=f"Too small: {file_size}")
        return 'skipped_too_small'

    if file_size > MAX_FILE_SIZE:
        db_update_status(download_url, 'skipped_too_large',
                        blocked_reason=f"Too large: {file_size}")
        return 'skipped_too_large'

    check_text = f"{identifier} {file_name} {lang_meta}"
    passed, reason = check_filters(check_text)
    if not passed:
        db_update_status(download_url, reason, blocked_reason=reason)
        return reason

    db_update_status(download_url, 'downloading')

    try:
        response = requests.get(
            download_url,
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
            headers={'User-Agent': 'ia-ppt-scraper/1.1'}
        )
        response.raise_for_status()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

    except Exception as e:
        db_update_status(download_url, 'failed', error=str(e))
        if os.path.exists(local_path):
            os.remove(local_path)
        return 'failed'

    try:
        file_hash = sha256_file(local_path)
        existing_hash = db_fetchone(
            "SELECT download_url FROM files WHERE sha256_hash=? AND status='uploaded_to_s3'",
            (file_hash,)
        )
        if existing_hash:
            db_update_status(download_url, 'skipped_duplicate',
                           blocked_reason=f"Duplicate of {existing_hash[0]}")
            os.remove(local_path)
            return 'skipped_duplicate'

        lang_detected = None
        if LANGDETECT_AVAILABLE and file_ext == '.pptx':
            lang_detected = detect_lang_from_pptx(local_path)
            if lang_detected in ('zh-cn', 'zh-tw', 'zh'):
                quarantine_key = f"ia-ppt-project/quarantine/{file_name}"
                upload_to_s3(local_path, quarantine_key)
                db_update_status(
                    download_url, 'skipped_chinese_mandarin',
                    lang_detected=lang_detected,
                    blocked_reason='Chinese detected post-download'
                )
                os.remove(local_path)
                return 'skipped_chinese_mandarin'

        quality_passed = True
        doc_metadata = {}
        quality_reason = "PPT file"

        if file_ext == '.pptx':
            quality_passed, doc_metadata, quality_reason = check_pptx_quality(
                local_path
            )

        if not quality_passed:
            db_update_status(
                download_url, 'failed',
                error=f"Quality: {quality_reason}"
            )
            os.remove(local_path)
            return 'failed_quality'

        url_hash = hashlib.md5(download_url.encode()).hexdigest()[:8]
        name_part = os.path.splitext(file_name)[0][:50]
        unique_filename = f"{name_part}_{url_hash}{file_ext}"

        day_folder = get_day_folder()
        s3_key = f"{day_folder}/files/{unique_filename}"
        file_id = hashlib.md5(download_url.encode()).hexdigest()
        collection_timestamp = datetime.now().isoformat()

        full_metadata = {
            'source_url': download_url,
            'file_id': file_id,
            'original_filename': file_name,
            'unique_filename': unique_filename,
            'file_format': file_ext.lstrip('.').upper(),
            'file_size_bytes': file_size,
            'file_size_mb': round(file_size / (1024*1024), 2),
            'download_url': download_url,
            'source_domain': 'archive.org',
            'organization_name': 'Internet Archive',
            'source_url_reachable': True,
            'source_url_status_code': 200,
            'collection_timestamp': collection_timestamp,
            'download_timestamp': collection_timestamp,
            'archive_identifier': identifier,
            'archive_item_url': f"https://archive.org/details/{identifier}",
            'license_or_rights': license_rights or '',
            'language_metadata': lang_meta or '',
            'language_detected': lang_detected or '',
            'title': doc_metadata.get('title', ''),
            'author': doc_metadata.get('author', ''),
            'organization': doc_metadata.get('organization', ''),
            'publication_date': doc_metadata.get('creation_date', ''),
            'modification_date': doc_metadata.get('modification_date', ''),
            'description': doc_metadata.get('description', ''),
            'keywords': doc_metadata.get('keywords', ''),
            'language': lang_detected or lang_meta or 'en',
            'slide_count': doc_metadata.get('slide_count', 0),
            'image_count': doc_metadata.get('image_count', 0),
            'chart_count': doc_metadata.get('chart_count', 0),
            'visual_density': doc_metadata.get('visual_density', 0),
            'quality_check': 'passed',
            'quality_reason': quality_reason,
            'day_folder': day_folder,
            's3_location': f"s3://{BUCKET}/{s3_key}",
            's3_bucket': BUCKET,
            's3_key': s3_key,
            'sha256_hash': file_hash,
            'crawl_metadata': {
                'crawler': 'ia-ppt-scraper-v1.1-node2',
                'crawl_method': 'internetarchive-api',
                'source_page': f"https://archive.org/details/{identifier}",
                'found_via': 'internetarchive-search',
            },
            'processing_metadata': {
                'quality_checker': 'QualityChecker-v2',
                'quality_check_passed': quality_passed,
                'quality_check_reason': quality_reason,
                'processed_at': collection_timestamp,
            },
            'tags': [
                'archive.org', day_folder,
                file_ext.lstrip('.').upper(),
                'presentation', identifier,
            ],
        }

        s3_meta = {
            'source-url': download_url[:500],
            'archive-identifier': identifier[:200],
            'file-id': file_id,
            'original-filename': file_name[:200],
            'sha256': file_hash,
        }
        upload_to_s3(local_path, s3_key, s3_meta)

        metadata_key = f"{day_folder}/metadata/{unique_filename}_{file_id}.json"
        upload_json_to_s3(full_metadata, metadata_key)

        db_update_status(
            download_url, 'uploaded_to_s3',
            s3_path=s3_key,
            sha256=file_hash,
            lang_detected=lang_detected
        )

        os.remove(local_path)

        log.info(
            f"✓ Uploaded: {unique_filename} "
            f"({round(file_size/1024)}KB) [{day_folder}]"
        )
        return 'uploaded_to_s3'

    except Exception as e:
        db_update_status(download_url, 'failed', error=str(e))
        if os.path.exists(local_path):
            os.remove(local_path)
        log.error(f"Error processing {file_name}: {e}")
        return 'failed'

# ============================================================
# DISCOVERY
# ============================================================
def discover_files_from_query(query):
    log.info(f"Searching: {query}")
    discovered = 0

    try:
        results = search_items(
            query,
            fields=[
                'identifier', 'title', 'creator', 'language',
                'licenseurl', 'subject', 'description',
                'source', 'collection', 'date', 'rights'
            ],
        )

        for result in results:
            identifier = result.get('identifier', '')
            if not identifier:
                continue

            check_text = (
                f"{identifier} {result.get('title','')} "
                f"{result.get('creator','')} {result.get('language','')}"
            )
            passed, reason = check_filters(check_text)
            if not passed:
                continue

            try:
                item = get_item(
                    identifier,
                    request_kwargs={'timeout': ITEM_TIMEOUT}
                )
                item_meta = item.metadata

                full_text = (
                    f"{identifier} {item_meta.get('title','')} "
                    f"{item_meta.get('creator','')} "
                    f"{item_meta.get('language','')} "
                    f"{item_meta.get('description','')} "
                    f"{item_meta.get('subject','')}"
                )
                passed, reason = check_filters(full_text)
                if not passed:
                    continue

                for f in item.files:
                    fname = f.get('name', '')
                    fsize = int(f.get('size', 0))
                    fext = os.path.splitext(fname)[1].lower()

                    if fext not in ('.ppt', '.pptx'):
                        continue

                    download_url = (
                        f"https://archive.org/download/{identifier}/{fname}"
                    )

                    existing = db_fetchone(
                        "SELECT id FROM files WHERE download_url=?",
                        (download_url,)
                    )
                    if existing:
                        continue

                    db_execute('''
                        INSERT OR IGNORE INTO files (
                            archive_identifier, archive_item_url,
                            file_name, file_extension, file_size,
                            download_url, source_domain,
                            license_or_rights, language_metadata,
                            status, created_at, updated_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (
                        identifier,
                        f"https://archive.org/details/{identifier}",
                        fname, fext, fsize, download_url,
                        'archive.org',
                        item_meta.get('licenseurl',
                                     item_meta.get('rights', '')),
                        item_meta.get('language', ''),
                        'queued',
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ))
                    discovered += 1

                time.sleep(DELAY_BETWEEN_ITEMS)

            except Exception as e:
                log.debug(f"Skipping {identifier}: {e}")
                continue

    except Exception as e:
        log.error(f"Search error for '{query}': {e}")

    log.info(f"Discovered {discovered} new files from: {query}")
    return discovered

# ============================================================
# WORKER
# ============================================================
def worker_thread(worker_id):
    log.info(f"Worker {worker_id} started")
    processed = 0

    while True:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                SELECT archive_identifier, file_name, file_size,
                       download_url, license_or_rights, language_metadata
                FROM files WHERE status="queued" LIMIT 1
            ''')
            row = c.fetchone()
            if row:
                c.execute(
                    "UPDATE files SET status='downloading', updated_at=? "
                    "WHERE download_url=?",
                    (datetime.now().isoformat(), row[3])
                )
                conn.commit()
            conn.close()

        if not row:
            time.sleep(5)
            continue

        (identifier, file_name, file_size,
         download_url, license_rights, lang_meta) = row

        process_file(
            identifier, file_name, file_size,
            download_url, license_rights, lang_meta
        )
        processed += 1

        if processed % 50 == 0:
            log.info(f"Worker {worker_id}: processed {processed} files")

        time.sleep(DELAY_BETWEEN_FILES)

# ============================================================
# STATS
# ============================================================
def print_stats():
    rows = db_fetchall('''
        SELECT status, COUNT(*) FROM files
        GROUP BY status ORDER BY COUNT(*) DESC
    ''')
    log.info("\n" + "="*50)
    log.info("STATS:")
    uploaded = 0
    for status, count in rows:
        log.info(f"  {status}: {count:,}")
        if status == 'uploaded_to_s3':
            uploaded = count
    log.info(f"  TOTAL UPLOADED: {uploaded:,}")
    log.info("="*50)
    return uploaded

# ============================================================
# MAIN
# ============================================================
def main():
    log.info("="*60)
    log.info("INTERNET ARCHIVE PPT SCRAPER v1.1 - NODE 2")
    log.info(f"Started: {datetime.now()}")
    log.info(f"Bucket: {BUCKET}")
    log.info(f"Workers: {MAX_WORKERS}")
    log.info("="*60)

    os.makedirs(SCRATCH_DIR, exist_ok=True)
    init_db()

    for i in range(MAX_WORKERS):
        t = threading.Thread(
            target=worker_thread, args=(i,), daemon=True
        )
        t.start()

    log.info(f"Started {MAX_WORKERS} worker threads")

    round_number = 0
    while True:
        round_number += 1
        log.info(f"\n{'='*60}")
        log.info(f"DISCOVERY ROUND {round_number} | {datetime.now()}")
        log.info(f"{'='*60}")

        total_discovered = 0
        for query in SEARCH_QUERIES:
            count = discover_files_from_query(query)
            total_discovered += count
            time.sleep(2)

        log.info(
            f"Round {round_number}: {total_discovered} new files discovered"
        )

        uploaded = print_stats()
        upload_db_to_s3()
        upload_log_to_s3()

        if uploaded >= 200000:
            log.info("TARGET REACHED: 200,000 files!")
            break

        log.info("Waiting 30 minutes before next discovery round...")
        time.sleep(1800)

if __name__ == '__main__':
    main()
```

### Step 4.3: Create the Zipper Script

```bash
nano /home/ubuntu/ppt-scraper/zipper.py
```

Paste:

```python
# ============================================================
# ZIPPER SCRIPT - Node 2
# Creates ZIP files from S3 daily collections
# Runs 3x daily via cron: 8AM, 2PM, 10PM
# ============================================================

import boto3
import json
import zipfile
import io
import gc
from datetime import datetime

BUCKET = 'research-documents-node2'
REGION = 'eu-north-1'
FILES_PER_ZIP = 200

s3 = boto3.client('s3', region_name=REGION)

def get_day_folders():
    response = s3.list_objects_v2(
        Bucket=BUCKET,
        Delimiter='/',
        Prefix='collection_02_presentations/'
    )
    folders = []
    for prefix in response.get('CommonPrefixes', []):
        folder = prefix['Prefix'].rstrip('/')
        if 'day_' in folder:
            folders.append(folder)
    return sorted(folders)

def list_day_files(day_folder):
    files = []
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(
        Bucket=BUCKET,
        Prefix=f'{day_folder}/files/'
    )
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Size'] > 0:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'filename': obj['Key'].split('/')[-1]
                })
    return files

def create_zip_batch(files_batch, zip_key):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zf:
        for file_info in files_batch:
            try:
                print(f"    Adding: {file_info['filename']}")
                obj = s3.get_object(
                    Bucket=BUCKET,
                    Key=file_info['key']
                )
                chunks = []
                for chunk in obj['Body'].iter_chunks(chunk_size=256*1024):
                    chunks.append(chunk)
                file_content = b''.join(chunks)
                zf.writestr(file_info['filename'], file_content)
                del file_content
                del chunks
                gc.collect()
            except Exception as e:
                print(f"    Skipping {file_info['filename']}: {e}")
                continue

    zip_buffer.seek(0)
    zip_size = zip_buffer.getbuffer().nbytes
    print(f"  Uploading {zip_key} ({round(zip_size/1024/1024, 1)} MB)...")
    s3.put_object(
        Bucket=BUCKET,
        Key=zip_key,
        Body=zip_buffer.getvalue(),
        ContentType='application/zip'
    )
    zip_buffer.close()
    gc.collect()
    print(f"  Done: {zip_key} ({round(zip_size/1024/1024, 1)} MB)")
    return zip_size

def zip_day(day_folder):
    print(f"\nZipping {day_folder}...")
    files = list_day_files(day_folder)
    if not files:
        print(f"  No files found")
        return []
    print(f"  Found {len(files)} files")
    batches = [
        files[i:i+FILES_PER_ZIP]
        for i in range(0, len(files), FILES_PER_ZIP)
    ]
    zip_manifest = []
    for idx, batch in enumerate(batches, 1):
        part_num = str(idx).zfill(3)
        day_name = day_folder.split('/')[-1]
        zip_key = f"{day_folder}/downloads/{day_name}_part_{part_num}.zip"
        print(f"\n  Part {idx}/{len(batches)} ({len(batch)} files)...")
        zip_size = create_zip_batch(batch, zip_key)
        zip_manifest.append({
            'part': idx,
            'total_parts': len(batches),
            'zip_key': zip_key,
            'zip_url': f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{zip_key}",
            'file_count': len(batch),
            'size_bytes': zip_size,
            'size_mb': round(zip_size/1024/1024, 1),
            'created_at': datetime.now().isoformat(),
        })
    return zip_manifest

def update_portal_manifest():
    print("\nUpdating portal manifest...")
    day_folders = get_day_folders()
    manifest = {
        'last_updated': datetime.now().isoformat(),
        'days': {}
    }
    for day_folder in day_folders:
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=f'{day_folder}/downloads/'
            )
            zips = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.zip'):
                    part_str = obj['Key'].split('_part_')[-1].replace('.zip', '')
                    try:
                        part_num = int(part_str)
                    except:
                        part_num = 0
                    zips.append({
                        'part': part_num,
                        'zip_key': obj['Key'],
                        'zip_url': f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{obj['Key']}",
                        'size_bytes': obj['Size'],
                        'size_mb': round(obj['Size']/1024/1024, 1),
                        'last_modified': obj['LastModified'].isoformat(),
                    })
            file_count = 0
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(
                Bucket=BUCKET,
                Prefix=f'{day_folder}/files/'
            ):
                file_count += len(page.get('Contents', []))
            manifest['days'][day_folder] = {
                'file_count': file_count,
                'zips': sorted(zips, key=lambda x: x['part']),
                'zip_count': len(zips),
                'last_zipped': datetime.now().isoformat() if zips else None,
            }
        except Exception as e:
            print(f"  Error: {e}")
    s3.put_object(
        Bucket=BUCKET,
        Key='portal_manifest.json',
        Body=json.dumps(manifest, indent=2, default=str).encode('utf-8'),
        ContentType='application/json'
    )
    print("  Manifest updated")

def main():
    print(f"\nZipper starting at {datetime.now()}")
    day_folders = get_day_folders()
    print(f"Day folders: {day_folders}")
    for day_folder in day_folders:
        zip_day(day_folder)
    update_portal_manifest()
    print(f"\nZipper complete at {datetime.now()}")

if __name__ == '__main__':
    main()
```

### Step 4.4: Create the Portal (index.html)

```bash
nano /home/ubuntu/ppt-scraper/index.html
```

Paste:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Document Archive - Node 2</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            color: #1a1a2e;
        }
        header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 24px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
        }
        header h1 { font-size: 22px; font-weight: 600; }
        header p { font-size: 13px; opacity: 0.7; margin-top: 4px; }
        .refresh-btn {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .refresh-btn:hover { background: rgba(255,255,255,0.1); }
        .container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .stat-card .number {
            font-size: 32px;
            font-weight: 700;
            color: #1a1a2e;
        }
        .stat-card.highlight .number { color: #0066cc; }
        .stat-card .label {
            font-size: 12px;
            color: #888;
            margin-top: 4px;
            text-transform: uppercase;
        }
        .progress-section {
            background: white;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .progress-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 13px;
        }
        .progress-bar-bg {
            background: #f0f0f0;
            border-radius: 8px;
            height: 10px;
            overflow: hidden;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #0066cc, #0099ff);
            height: 100%;
            border-radius: 8px;
            transition: width 1s ease;
        }
        .day-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            overflow: hidden;
            margin-bottom: 20px;
        }
        .day-header {
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
        }
        .day-header:hover { background: #fafafa; }
        .day-badge {
            background: #1a1a2e;
            color: white;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
            margin-right: 12px;
        }
        .day-badge.active { background: #0066cc; }
        .zip-section {
            padding: 20px 24px;
            background: #f8fbff;
            border-bottom: 1px solid #e8f0fe;
        }
        .zip-title {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .zip-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 8px;
        }
        .zip-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 10px 18px;
            background: #0066cc;
            color: white;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s;
        }
        .zip-btn:hover { background: #0052a3; }
        .zip-size {
            font-size: 11px;
            opacity: 0.8;
            margin-top: 2px;
        }
        .zip-note {
            font-size: 11px;
            color: #888;
        }
        .files-toggle {
            padding: 14px 24px;
            cursor: pointer;
            font-size: 13px;
            color: #0066cc;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #f0f0f0;
        }
        .files-toggle:hover { background: #fafafa; }
        .files-section { padding: 0 24px 24px; display: none; }
        .files-section.open { display: block; }
        .search-box {
            padding: 8px 14px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 13px;
            width: 250px;
            outline: none;
            margin: 16px 0;
        }
        .files-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .files-table th {
            text-align: left;
            padding: 10px 12px;
            background: #f8f9fa;
            color: #666;
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 1px solid #eee;
        }
        .files-table td {
            padding: 12px;
            border-bottom: 1px solid #f5f5f5;
            vertical-align: middle;
        }
        .files-table tr:hover td { background: #fafafa; }
        .file-name {
            font-weight: 500;
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        .badge-pptx { background: #fff4e6; color: #cc6600; }
        .badge-ppt { background: #fff0f0; color: #cc0000; }
        .btn {
            padding: 6px 14px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary { background: #0066cc; color: white; }
        .btn-primary:hover { background: #0052a3; }
        .btn-outline { background: transparent; border: 1px solid #ddd; color: #444; }
        .btn-outline:hover { background: #f5f5f5; }
        .loading {
            text-align: center;
            padding: 60px;
            color: #888;
        }
        .spinner {
            width: 36px;
            height: 36px;
            border: 3px solid #eee;
            border-top-color: #0066cc;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        footer {
            text-align: center;
            padding: 30px;
            color: #aaa;
            font-size: 12px;
        }
        @media (max-width: 768px) {
            .stats-bar { grid-template-columns: repeat(2, 1fr); }
            header { padding: 16px 20px; flex-direction: column; gap: 10px; }
        }
    </style>
</head>
<body>
<header>
    <div>
        <h1>📚 Research Document Archive — Node 2</h1>
        <p>PowerPoint presentations collected from Internet Archive</p>
    </div>
    <div style="text-align:right">
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        <div style="font-size:11px;opacity:0.5;margin-top:6px" id="lastUpdated">Loading...</div>
    </div>
</header>

<div class="container">
    <div class="stats-bar">
        <div class="stat-card highlight">
            <div class="number" id="totalFiles">—</div>
            <div class="label">Total Files</div>
        </div>
        <div class="stat-card">
            <div class="number" id="totalSize">—</div>
            <div class="label">Total Size</div>
        </div>
        <div class="stat-card">
            <div class="number" id="daysActive">—</div>
            <div class="label">Days Active</div>
        </div>
        <div class="stat-card">
            <div class="number" id="daysRemaining">—</div>
            <div class="label">Days Remaining</div>
        </div>
    </div>

    <div class="progress-section">
        <div class="progress-header">
            <span>📈 Progress toward 200,000 file target</span>
            <span id="progressText">0 / 200,000</span>
        </div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" id="progressBar" style="width:0%"></div>
        </div>
    </div>

    <div id="daysContainer">
        <div class="loading">
            <div class="spinner"></div>
            <p>Loading archive...</p>
        </div>
    </div>
</div>

<footer>
    Research Document Archive Node 2 &bull;
    Files collected from Internet Archive &bull;
    Updated 3x daily
</footer>

<script>
const BUCKET = 'research-documents-node2';
const REGION = 'eu-north-1';
const BASE_URL = `https://${BUCKET}.s3.${REGION}.amazonaws.com`;
const TARGET_FILES = 200000;
const FILES_PER_PAGE = 20;
const START_DATE = new Date('2026-06-28');
const END_DATE = new Date('2026-07-03');

const DAY_NAMES = {
    'collection_02_presentations/day_001': 'Day 1 — Saturday, June 28',
    'collection_02_presentations/day_002': 'Day 2 — Sunday, June 29',
    'collection_02_presentations/day_003': 'Day 3 — Monday, June 30',
    'collection_02_presentations/day_004': 'Day 4 — Tuesday, July 1',
    'collection_02_presentations/day_005': 'Day 5 — Wednesday, July 2',
    'collection_02_presentations/day_006': 'Day 6 — Thursday, July 3',
};

let allDaysData = {};
let portalManifest = null;
let totalFilesCount = 0;
let totalSizeBytes = 0;

function formatSize(bytes) {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
    if (bytes < 1024*1024*1024) return (bytes/(1024*1024)).toFixed(1) + ' MB';
    return (bytes/(1024*1024*1024)).toFixed(2) + ' GB';
}

function formatDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('en-GB', {
        day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'
    });
}

function getNextUpdateTime() {
    const now = new Date();
    const hours = [8, 14, 22];
    for (const h of hours) {
        if (now.getHours() < h) {
            const next = new Date(now);
            next.setHours(h, 0, 0, 0);
            return next.toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit'});
        }
    }
    return 'Tomorrow 8:00 AM';
}

function getFileExt(filename) {
    const parts = filename.split('.');
    return parts[parts.length-1].toUpperCase();
}

async function listS3Files(prefix, maxKeys=2000) {
    const url = `${BASE_URL}?list-type=2&prefix=${encodeURIComponent(prefix)}&max-keys=${maxKeys}`;
    try {
        const resp = await fetch(url);
        const text = await resp.text();
        const xml = new DOMParser().parseFromString(text, 'text/xml');
        return Array.from(xml.querySelectorAll('Contents')).map(item => ({
            key: item.querySelector('Key').textContent,
            size: parseInt(item.querySelector('Size').textContent),
            lastModified: item.querySelector('LastModified').textContent,
        })).filter(f => f.size > 0);
    } catch(e) { return []; }
}

async function listS3Prefixes(prefix) {
    const url = `${BASE_URL}?list-type=2&prefix=${encodeURIComponent(prefix)}&delimiter=/&max-keys=50`;
    try {
        const resp = await fetch(url);
        const text = await resp.text();
        const xml = new DOMParser().parseFromString(text, 'text/xml');
        return Array.from(xml.querySelectorAll('CommonPrefixes Prefix')).map(p => p.textContent);
    } catch(e) { return []; }
}

function buildFileUrl(key) {
    return `${BASE_URL}/${key.split('/').map(p => encodeURIComponent(decodeURIComponent(p))).join('/')}`;
}

function renderFileRow(file) {
    const filename = decodeURIComponent(file.key.split('/').pop());
    const ext = getFileExt(filename);
    const badgeClass = ext === 'PPTX' ? 'badge-pptx' : 'badge-ppt';
    const fileUrl = buildFileUrl(file.key);
    return `
        <tr>
            <td>
                <div class="file-name" title="${filename}">${filename}</div>
                <div style="font-size:11px;color:#aaa;margin-top:2px">${formatDate(file.lastModified)}</div>
            </td>
            <td><span class="badge ${badgeClass}">${ext}</span></td>
            <td>${formatSize(file.size)}</td>
            <td>
                <div style="display:flex;gap:6px">
                    <a href="${fileUrl}" target="_blank">
                        <button class="btn btn-outline">👁 Preview</button>
                    </a>
                    <a href="${fileUrl}" download="${filename}">
                        <button class="btn btn-primary">⬇ Download</button>
                    </a>
                </div>
            </td>
        </tr>`;
}

function renderZipSection(dayFolder) {
    const dayData = portalManifest?.days?.[dayFolder];
    const zips = dayData?.zips || [];
    const lastZipped = dayData?.last_zipped;
    const nextUpdate = getNextUpdateTime();

    if (zips.length === 0) {
        return `
            <div class="zip-section">
                <div class="zip-title">📦 ZIP Downloads</div>
                <p style="font-size:13px;color:#888">ZIP files are being prepared. Next update: ${nextUpdate}</p>
            </div>`;
    }

    const totalZipSize = zips.reduce((acc, z) => acc + z.size_bytes, 0);
    return `
        <div class="zip-section">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div class="zip-title">📦 ZIP Downloads
                    <span style="font-weight:400;color:#888;font-size:12px;margin-left:8px">
                        ${zips.length} part${zips.length>1?'s':''} &bull;
                        ${formatSize(totalZipSize)} total &bull;
                        Updated: ${formatDate(lastZipped)}
                    </span>
                </div>
                <span style="font-size:11px;background:#fff3cd;color:#856404;padding:3px 10px;border-radius:4px">
                    ⏰ Next: ${nextUpdate}
                </span>
            </div>
            <div class="zip-buttons">
                ${zips.map(zip => `
                    <a href="${zip.zip_url}" download class="zip-btn">
                        ⬇ Part ${zip.part}
                        <span class="zip-size">${zip.size_mb} MB</span>
                    </a>
                `).join('')}
            </div>
            <div class="zip-note">
                💡 Download all ${zips.length} part${zips.length>1?'s':''} for complete collection.
            </div>
        </div>`;
}

function renderDayCard(dayFolder, files, isFirst) {
    const dayName = DAY_NAMES[dayFolder] || dayFolder;
    const fileCount = files.length;
    const daySize = files.reduce((acc, f) => acc + f.size, 0);
    const isActive = fileCount > 0;
    const pptxCount = files.filter(f => f.key.toLowerCase().endsWith('.pptx')).length;
    const pptCount = files.filter(f => f.key.toLowerCase().endsWith('.ppt')).length;
    const isOpen = isFirst;
    const dayNum = dayFolder.split('day_')[1];

    const fileRows = files.slice(0, FILES_PER_PAGE).map(renderFileRow).join('');
    const hasMore = files.length > FILES_PER_PAGE;

    return `
        <div class="day-card" id="card-${dayNum}">
            <div class="day-header" onclick="toggleDay('${dayNum}')">
                <div style="display:flex;align-items:center">
                    <span class="day-badge ${isActive?'active':''}">DAY ${parseInt(dayNum)}</span>
                    <div>
                        <div style="font-weight:600;font-size:14px">${dayName}</div>
                        <div style="font-size:12px;color:#888;margin-top:2px">
                            ${fileCount > 0
                                ? `${fileCount.toLocaleString()} files &bull; ${formatSize(daySize)}`
                                : 'Collection not yet started'}
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:16px;align-items:center">
                    ${fileCount > 0 ? `
                        <span style="font-size:13px;color:#666">📊 <strong>${pptxCount}</strong> PPTX</span>
                        <span style="font-size:13px;color:#666">📄 <strong>${pptCount}</strong> PPT</span>
                    ` : ''}
                    <span style="color:#bbb;font-size:18px" id="arrow-${dayNum}">${isOpen?'▲':'▼'}</span>
                </div>
            </div>

            <div id="section-${dayNum}" style="display:${isOpen?'block':'none'}">
                ${renderZipSection(dayFolder)}

                ${fileCount > 0 ? `
                    <div class="files-toggle" onclick="toggleFiles('${dayNum}')">
                        <span>📁 Browse individual files (${fileCount.toLocaleString()} total)</span>
                        <span id="files-arrow-${dayNum}">▼ Show</span>
                    </div>
                    <div class="files-section" id="files-${dayNum}">
                        <input type="text" class="search-box"
                            placeholder="Search filenames..."
                            onkeyup="filterFiles('${dayNum}', '${dayFolder}', this.value)" />
                        <table class="files-table">
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Type</th>
                                    <th>Size</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-${dayNum}">${fileRows}</tbody>
                        </table>
                        ${hasMore ? `
                            <div style="text-align:center;padding:16px;border-top:1px solid #f0f0f0">
                                <button class="btn btn-outline"
                                    onclick="loadMore('${dayNum}', '${dayFolder}', ${FILES_PER_PAGE})">
                                    Load more (${(fileCount-FILES_PER_PAGE).toLocaleString()} remaining)
                                </button>
                            </div>` : ''}
                    </div>
                ` : `
                    <div style="text-align:center;padding:40px;color:#888">
                        ⏳ Files will appear here once collection begins.
                    </div>
                `}
            </div>
        </div>`;
}

function toggleDay(dayNum) {
    const section = document.getElementById(`section-${dayNum}`);
    const arrow = document.getElementById(`arrow-${dayNum}`);
    const isOpen = section.style.display !== 'none';
    section.style.display = isOpen ? 'none' : 'block';
    arrow.textContent = isOpen ? '▼' : '▲';
}

function toggleFiles(dayNum) {
    const section = document.getElementById(`files-${dayNum}`);
    const arrow = document.getElementById(`files-arrow-${dayNum}`);
    const isOpen = section.classList.contains('open');
    section.classList.toggle('open');
    arrow.textContent = isOpen ? '▼ Show' : '▲ Hide';
}

function filterFiles(dayNum, dayFolder, query) {
    const tbody = document.getElementById(`tbody-${dayNum}`);
    const files = allDaysData[dayFolder] || [];
    const filtered = query
        ? files.filter(f => f.key.toLowerCase().includes(query.toLowerCase()))
        : files;
    tbody.innerHTML = filtered.slice(0, 100).map(renderFileRow).join('') ||
        '<tr><td colspan="4" style="text-align:center;padding:20px;color:#888">No files match</td></tr>';
}

function loadMore(dayNum, dayFolder, offset) {
    const files = allDaysData[dayFolder] || [];
    const tbody = document.getElementById(`tbody-${dayNum}`);
    tbody.innerHTML += files.slice(offset, offset+FILES_PER_PAGE).map(renderFileRow).join('');
    const newOffset = offset + FILES_PER_PAGE;
    const btn = document.querySelector(`#card-${dayNum} [onclick*="loadMore"]`)?.parentElement;
    if (btn) {
        if (newOffset >= files.length) {
            btn.remove();
        } else {
            btn.innerHTML = `<button class="btn btn-outline"
                onclick="loadMore('${dayNum}', '${dayFolder}', ${newOffset})">
                Load more (${(files.length-newOffset).toLocaleString()} remaining)
            </button>`;
        }
    }
}

async function init() {
    const container = document.getElementById('daysContainer');

    try {
        const resp = await fetch(`${BASE_URL}/portal_manifest.json?t=${Date.now()}`);
        if (resp.ok) portalManifest = await resp.json();
    } catch(e) {}

    const prefixes = await listS3Prefixes('collection_02_presentations/');
    const dayFolders = prefixes
        .filter(p => p.includes('day_'))
        .map(p => p.replace(/\/$/, ''))
        .sort();

    let cards = '';
    let isFirst = true;

    for (const dayFolder of dayFolders) {
        const files = await listS3Files(`${dayFolder}/files/`, 5000);
        allDaysData[dayFolder] = files;
        totalFilesCount += files.length;
        totalSizeBytes += files.reduce((acc, f) => acc + f.size, 0);
        cards += renderDayCard(dayFolder, files, isFirst);
        isFirst = false;
    }

    for (const dayKey of Object.keys(DAY_NAMES)) {
        if (!dayFolders.includes(dayKey)) {
            allDaysData[dayKey] = [];
            cards += renderDayCard(dayKey, [], false);
        }
    }

    container.innerHTML = cards || '<div style="text-align:center;padding:60px;color:#888">No files yet. Check back soon.</div>';

    const daysActive = dayFolders.length;
    const daysRemaining = Math.max(0, Math.ceil((END_DATE - new Date()) / (1000*60*60*24)));

    document.getElementById('totalFiles').textContent = totalFilesCount.toLocaleString();
    document.getElementById('totalSize').textContent = formatSize(totalSizeBytes);
    document.getElementById('daysActive').textContent = daysActive;
    document.getElementById('daysRemaining').textContent = daysRemaining;

    const pct = Math.min((totalFilesCount/TARGET_FILES)*100, 100).toFixed(1);
    document.getElementById('progressBar').style.width = pct + '%';
    document.getElementById('progressText').textContent =
        `${totalFilesCount.toLocaleString()} / ${TARGET_FILES.toLocaleString()} (${pct}%)`;
    document.getElementById('lastUpdated').textContent =
        `Last refreshed: ${new Date().toLocaleTimeString()}`;
}

setInterval(() => location.reload(), 5 * 60 * 1000);
init();
</script>
</body>
</html>
```

---

## PART 5: UPLOAD PORTAL AND CONFIGURE

### Step 5.1: Upload index.html to S3

```bash
cd /home/ubuntu/ppt-scraper
aws s3 cp index.html s3://research-documents-node2/index.html \
    --content-type "text/html" \
    --cache-control "no-cache"
```

### Step 5.2: Set Up CloudFront (HTTPS)

1. Go to AWS Console → CloudFront
2. Click "Create distribution"
3. Origin domain: `research-documents-node2.s3-website.eu-north-1.amazonaws.com`
4. Protocol: HTTP only
5. Viewer protocol policy: Redirect HTTP to HTTPS
6. Default root object: `index.html`
7. Click "Create distribution"
8. Wait 5-10 minutes
9. Copy your CloudFront URL (looks like `https://XXXXX.cloudfront.net`)

---

## PART 6: SET UP AUTOMATIC ZIPPING

```bash
# Install cron
sudo apt install -y cron
sudo systemctl start cron
sudo systemctl enable cron

# Add cron jobs
crontab -e
```

In the editor (vim), press `i` to enter insert mode, then paste:

```
0 8 * * * cd /home/ubuntu/ppt-scraper && source venv/bin/activate && python3 zipper.py >> zipper.log 2>&1
0 14 * * * cd /home/ubuntu/ppt-scraper && source venv/bin/activate && python3 zipper.py >> zipper.log 2>&1
0 22 * * * cd /home/ubuntu/ppt-scraper && source venv/bin/activate && python3 zipper.py >> zipper.log 2>&1
```

Press `Esc`, then type `:wq` and press `Enter` to save.

Verify:
```bash
crontab -l
```

---

## PART 7: RUN THE SCRAPER

```bash
cd /home/ubuntu/ppt-scraper
source venv/bin/activate

# Test first (watch for 3 minutes)
python3 ia_scraper.py
```

You should see:
```
INTERNET ARCHIVE PPT SCRAPER v1.1 - NODE 2
Started 30 worker threads
Searching: pptx presentation slides
✓ Uploaded: filename_abc12345.pptx (2.3MB)
```

Once confirmed working, stop test and run permanently:

```bash
Ctrl+C

nohup python3 ia_scraper.py > nohup_ia.out 2>&1 &
echo "PID: $!"
```

Verify running:
```bash
tail -f nohup_ia.out
```

Press `Ctrl+C` to stop watching — scraper keeps running.

---

## PART 8: CHECK PROGRESS ANYTIME

```bash
# Connect to EC2
ssh -i node2-key.pem ubuntu@YOUR_EC2_IP

# Check scraper is running
ps aux | grep ia_scraper | grep -v grep

# Watch live output
cd /home/ubuntu/ppt-scraper
source venv/bin/activate
tail -f nohup_ia.out

# Check database stats
python3 -c "
import sqlite3
conn = sqlite3.connect('ia_scraper.db')
c = conn.cursor()
c.execute('SELECT status, COUNT(*) FROM files GROUP BY status ORDER BY COUNT(*) DESC')
for row in c.fetchall():
    print(f'{row[0]}: {row[1]:,}')
conn.close()
"

# Check S3 file count
aws s3 ls s3://research-documents-node2/collection_02_presentations/ --recursive | grep "/files/" | wc -l
```

---

## PART 9: THURSDAY JULY 3 SHUTDOWN

```bash
# Stop scraper
kill $(pgrep -f ia_scraper.py)

# Final backup
cd /home/ubuntu/ppt-scraper
source venv/bin/activate
python3 -c "
from ia_scraper import upload_db_to_s3, upload_log_to_s3
upload_db_to_s3()
upload_log_to_s3()
print('Done')
"

# Exit
exit
```

Then in AWS Console:
1. Go to EC2 → Instances
2. Select your instance
3. Actions → Instance State → **TERMINATE** (NOT stop)

---

## SUMMARY

| Item | Value |
|------|-------|
| S3 Bucket | research-documents-node2 |
| EC2 Type | t3.small Ubuntu |
| Region | eu-north-1 (Stockholm) |
| Workers | 30 parallel |
| Target | 200,000 files |
| Deadline | July 3, 2026 |
| Cost | ~$0 (free tier) |

**Share your CloudFront URL with the project owner when ready.**

---

*Guide version 1.0 — June 30, 2026*

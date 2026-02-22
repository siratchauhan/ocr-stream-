
# 📄 OCR Document Intelligence App

A full-featured OCR-based document extraction system built with Streamlit and Supabase.

This application extracts structured data from multiple Indian government ID documents and securely stores both images and extracted data with user-level isolation.

LIVE DEMO=https://ocr-stream-nhjd5pbhtxcm99hfgncbre.streamlit.app/
---

# 🚀 Features

### 📤 Upload Options

* Image upload (JPG, PNG)
* Camera capture
* Multi-page PDF support

### 🪪 Supported Documents

* Aadhaar Card
* PAN Card
* Driving License
* Voter ID
* Custom document parsing

### 🔍 OCR Processing

* OCR powered via OCR.space API
* Structured field extraction using regex parsing
* Raw text preservation

### 🗄 Backend

* Supabase Database (PostgreSQL)
* Supabase Storage (Private Bucket)
* Row Level Security (RLS) enabled
* User-based data separation

---

# 🛠 Tech Stack

* Python
* Streamlit
* OCR.space API
* Supabase (Auth + Database + Storage)
* PostgreSQL
* python-dotenv

---

# 🏗 System Architecture

```
User Upload
     ↓
Streamlit App
     ↓
OCR.space API
     ↓
Structured Parsing
     ↓
Supabase Storage (Image)
     ↓
Supabase Database (Extracted Data)
```

---


# 🖼 Supabase Storage Setup

1. Create a bucket
2. Disable **Public bucket**
3. Enable file size restriction
4. Enable MIME restriction (image/jpeg, image/png, application/pdf)


# 🔑 Environment Variables

Create `.env` file:

```
OCR_API_KEY=your_ocr_api_key
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

⚠️ Never push `.env` to GitHub
⚠️ Add `.env` to `.gitignore`


# ▶️ Run Locally

### 1️⃣ Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run App

```bash
streamlit run app.py
```

---

# ☁️ Deployment

1. Push code to GitHub
2. Connect repo to Streamlit Cloud
3. Add secrets in App Settings

Example:

```
OCR_API_KEY = "your_key"
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_SERVICE_KEY = "your_key"
```

---

# 🔐 Security Features

* Row Level Security enabled
* Private storage bucket
* User-based access control
* No public image exposure
* Environment variable protection

---

# 📌 Future Enhancements

* Full Supabase Authentication UI
* Admin dashboard
* Download extracted data as CSV
* Analytics dashboard
* Document verification scoring

---

# 🏆 Project Highlights

* Multi-document OCR intelligence
* Scalable database design (JSONB-based)
* Secure cloud architecture
* Production-ready structure
* Clean Git workflow

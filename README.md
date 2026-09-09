# 📊 Student Performance Analytics Dashboard

> A simple Streamlit-based dashboard that allows students to upload academic marks data and visualize and analyze their performance.

---

## Features

- **CSV upload** — upload marks data in CSV format
- **Excel upload** — upload marks data in `.xlsx` or `.xls` format
- **Data validation** — friendly error messages for missing columns, invalid values, and out-of-range marks
- **Data cleaning** — normalises column names, converts types, removes exact duplicates
- **Percentage calculation** — computed as `(Marks / Max_Marks) × 100`
- **Interactive visualizations** — subject bar chart, marks vs max grouped bar, semester trend line, distribution histogram
- **Performance KPIs** — Overall %, Average Marks, Best Subject, Weakest Subject
- **Semester trend** — line chart showing improvement / decline across semesters
- **Basic insights** — rule-based text insights about performance
- **Filterable dashboard** — filter by Semester and Subject; all charts update accordingly
- **Weak subject detection** — configurable threshold slider (default 60%)
- **Processed CSV download** — download the cleaned data including the Percentage column

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.x | Core language |
| Streamlit | Web application framework |
| Pandas | Data manipulation |
| NumPy | Numeric operations |
| Plotly | Interactive charts |
| OpenPyXL | Excel file reading (.xlsx) |

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd student-performance-analytics
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

---

## Dataset Format

Your file must contain at least these four columns:

| Column | Type | Description |
|---|---|---|
| `Subject` | String | Name of the subject |
| `Marks` | Number | Marks obtained |
| `Max_Marks` | Number | Maximum marks for that exam |
| `Semester` | Number | Semester number |

### Optional columns

| Column | Type | Description |
|---|---|---|
| `Exam_Type` | String | e.g. Midterm, Final |
| `Date` | String / Date | Date of the exam |

### Example

```
Subject,Marks,Max_Marks,Semester,Exam_Type
Data Structures,85,100,1,Midterm
DBMS,78,100,1,Midterm
Operating Systems,91,100,1,Midterm
Mathematics,72,100,1,Final
Computer Networks,88,100,2,Final
```

A ready-to-use sample file is provided at `sample_data/sample_marks.csv`.

> ⚠️ The sample file is NOT automatically loaded. You must upload it manually via the application.

---

## Project Structure

```
student-performance-analytics/
│
├── app.py                        # Main entry point — page config + navigation
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── .gitignore
│
├── pages/
│   ├── upload.py                 # Data Upload page
│   └── visualization.py          # Visualization & Analysis page
│
├── utils/
│   ├── __init__.py
│   ├── data_processing.py        # File reading, cleaning, percentage calc
│   └── validation.py             # All data validation logic
│
└── sample_data/
    └── sample_marks.csv          # Sample dataset for testing
```

---

## Limitations

- **Temporary data** — data exists only during the active Streamlit session. Refreshing the browser clears it.
- **No user accounts** — there is no login, registration, or user management.
- **No database** — data is not persisted between sessions.
- **No ML predictions** — the application provides only rule-based insights; no machine learning is used.
- **Single user** — the application is designed for a single user's local use.

---

## Future Scope

The following features are intentionally out of scope for this MVP and may be considered for future versions:

- User authentication and multiple user support
- Database storage (PostgreSQL / SQLite)
- Student profiles and attendance tracking
- CGPA / SGPA calculation
- PDF report generation
- Machine learning–based performance prediction
- Personalized study recommendations
- Cloud deployment
- Admin / teacher dashboard
- Institution-level analytics
